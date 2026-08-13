"""Evidence-only extraction of tactical slots from Football Manager pitches."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import dist
import re
from typing import Any

import cv2
import numpy as np

from fmsat.core.ocr import OcrEngine, OcrResult

from .tacticModels import FormationSlot, TacticalPhase, TacticIssue, ValidationState
from .tacticVocabulary import TacticVocabulary


@dataclass(frozen=True, slots=True)
class FormationExtractResult:
    """Observed phase slots and extraction issues from a Formation screen."""

    slots: tuple[FormationSlot, ...]
    issues: tuple[TacticIssue, ...]


class PitchZoneClassifier:
    """Classify normalized pitch centres using configurable depth and width zones."""

    def __init__(self, zones: dict[str, Any]) -> None:
        self.zones = zones

    def positionClassify(self, x: float, y: float) -> str | None:
        """Return the canonical position configured for one normalized centre."""

        for band in self.zones.get("bands", []):
            if float(band["yMin"]) <= y < float(band["yMax"]):
                for zone in band.get("positions", []):
                    if float(zone["xMin"]) <= x < float(zone["xMax"]):
                        return str(zone["code"])
        return None


class FormationPhaseLinker:
    """Assign stable slot IDs across phases without manufacturing uncertain links."""

    def __init__(
        self,
        maximumDistance: float = 0.38,
        ambiguityMargin: float = 0.05,
        orderWeight: float = 0.08,
    ) -> None:
        self.maximumDistance = maximumDistance
        self.ambiguityMargin = ambiguityMargin
        self.orderWeight = orderWeight

    def phasesLink(
        self,
        inPossession: list[FormationSlot],
        outOfPossession: list[FormationSlot],
    ) -> tuple[list[FormationSlot], list[FormationSlot], list[TacticIssue]]:
        """Link exact players first, then only unambiguous spatial neighbours."""

        linkedIn = [replace(slot, slotId=f"slot-{index:02d}") for index, slot in enumerate(
            sorted(inPossession, key=lambda item: (item.y, item.x)), start=1
        )]
        available = set(range(len(outOfPossession)))
        matches: dict[int, int] = {}
        issues: list[TacticIssue] = []

        # A displayed player is the strongest identity available in the current model.
        for inIndex, source in enumerate(linkedIn):
            if not source.displayedPlayer:
                continue
            candidates = [
                index
                for index in available
                if outOfPossession[index].displayedPlayer
                and self._playerName(outOfPossession[index].displayedPlayer)
                == self._playerName(source.displayedPlayer)
            ]
            if len(candidates) == 1:
                matches[inIndex] = candidates[0]
                available.remove(candidates[0])
            elif len(candidates) > 1:
                issues.append(TacticIssue(
                    "ambiguousPhaseLink",
                    f"Player {source.displayedPlayer!r} appears in multiple "
                    "out-of-possession slots",
                    source.displayedPlayer,
                ))

        # Shirt number survives OCR in some skins even where the name does not.
        for inIndex, source in enumerate(linkedIn):
            number = self._shirtNumber(source.displayedPlayer)
            if inIndex in matches or number is None:
                continue
            candidates = [
                index
                for index in available
                if self._shirtNumber(outOfPossession[index].displayedPlayer) == number
            ]
            if len(candidates) == 1:
                matches[inIndex] = candidates[0]
                available.remove(candidates[0])
            elif len(candidates) > 1:
                issues.append(TacticIssue(
                    "ambiguousPhaseLink",
                    f"Shirt number {number} appears in multiple out-of-possession slots",
                    str(number),
                ))

        # Spatial matching is accepted only where the nearest candidate is clearly best.
        for inIndex, source in enumerate(linkedIn):
            if inIndex in matches or not available:
                continue
            candidates = sorted(
                self._candidateScore(
                    source,
                    inIndex,
                    len(linkedIn),
                    outOfPossession[index],
                    index,
                    len(outOfPossession),
                )
                for index in available
            )
            nearestScore, nearestDistance, nearestIndex = candidates[0]
            ambiguous = (
                len(candidates) > 1
                and candidates[1][0] - nearestScore < self.ambiguityMargin
            )
            if nearestDistance <= self.maximumDistance and not ambiguous:
                matches[inIndex] = nearestIndex
                available.remove(nearestIndex)
            else:
                issues.append(TacticIssue(
                    "uncertainPhaseLink",
                    f"Could not safely link in-possession slot at ({source.x:.3f}, {source.y:.3f})",
                ))

        reverseMatches = {target: source for source, target in matches.items()}
        nextId = len(linkedIn) + 1
        linkedOut: list[FormationSlot] = []
        for outIndex, slot in enumerate(outOfPossession):
            if outIndex in reverseMatches:
                slotId = linkedIn[reverseMatches[outIndex]].slotId
            else:
                slotId = f"slot-{nextId:02d}"
                nextId += 1
                issues.append(TacticIssue(
                    "unmatchedPhaseSlot",
                    f"Out-of-possession slot at ({slot.x:.3f}, {slot.y:.3f}) is unmatched",
                ))
            linkedOut.append(replace(slot, slotId=slotId))
        return linkedIn, linkedOut, issues

    def _candidateScore(
        self,
        source: FormationSlot,
        sourceIndex: int,
        sourceCount: int,
        target: FormationSlot,
        targetIndex: int,
        targetCount: int,
    ) -> tuple[float, float, int]:
        """Rank spatial neighbours with relative pitch ordering as a tie-breaker."""

        spatialDistance = dist((source.x, source.y), (target.x, target.y))
        sourceOrder = sourceIndex / max(1, sourceCount - 1)
        targetOrder = targetIndex / max(1, targetCount - 1)
        score = spatialDistance + abs(sourceOrder - targetOrder) * self.orderWeight
        return score, spatialDistance, targetIndex

    @staticmethod
    def _playerName(value: str | None) -> str:
        """Normalize a displayed player while ignoring a leading shirt number."""

        return re.sub(r"^\s*\d{1,2}\s+", "", value or "").strip().casefold()

    @staticmethod
    def _shirtNumber(value: str | None) -> int | None:
        """Return a leading displayed shirt number when OCR retained one."""

        match = re.match(r"^\s*(\d{1,2})\b", value or "")
        return int(match.group(1)) if match else None


class TacticFormationExtractor:
    """Detect role tiles before running focused OCR on each detected crop."""

    def __init__(
        self,
        ocr: OcrEngine,
        vocabulary: TacticVocabulary,
        configuration: dict[str, Any],
    ) -> None:
        self.ocr = ocr
        self.vocabulary = vocabulary
        self.configuration = configuration
        self.classifier = PitchZoneClassifier(configuration.get("pitchZones", {}))
        linking = configuration.get("linking", {})
        self.linker = FormationPhaseLinker(
            float(linking.get("maximumDistance", 0.38)),
            float(linking.get("ambiguityMargin", 0.05)),
            float(linking.get("orderWeight", 0.08)),
        )

    def formationExtract(self, image: np.ndarray, sourceImport: str) -> FormationExtractResult:
        """Extract and cross-link both phase pitches from a Formation screenshot."""

        issues: list[TacticIssue] = []
        phases: dict[TacticalPhase, list[FormationSlot]] = {}
        for phase in (TacticalPhase.IN_POSSESSION, TacticalPhase.OUT_OF_POSSESSION):
            region = self.configuration.get("phaseRegions", {}).get(phase.value)
            if not isinstance(region, dict):
                issues.append(TacticIssue(
                    "missingPitchRegion",
                    f"No {phase.value} pitch region is configured",
                ))
                phases[phase] = []
                continue
            pitch = self._regionCrop(image, region)
            slots, phaseIssues = self._phaseExtract(pitch, phase, sourceImport)
            phases[phase] = slots
            issues.extend(phaseIssues)

        linkedIn, linkedOut, linkIssues = self.linker.phasesLink(
            phases[TacticalPhase.IN_POSSESSION],
            phases[TacticalPhase.OUT_OF_POSSESSION],
        )
        issues.extend(linkIssues)
        return FormationExtractResult(tuple(linkedIn + linkedOut), tuple(issues))

    def _phaseExtract(
        self,
        pitch: np.ndarray,
        phase: TacticalPhase,
        sourceImport: str,
    ) -> tuple[list[FormationSlot], list[TacticIssue]]:
        if pitch.size == 0:
            return [], [TacticIssue(
                "emptyPitchRegion",
                f"Configured {phase.value} pitch region is empty",
            )]
        boxes = self._tilesDetect(pitch)
        issues: list[TacticIssue] = []
        if not boxes:
            return [], [TacticIssue(
                "missingFormationSlots",
                f"No {phase.value} role tiles were detected",
            )]
        height, width = pitch.shape[:2]
        slots: list[FormationSlot] = []
        for index, (left, top, right, bottom) in enumerate(boxes, start=1):
            crop = pitch[top:bottom, left:right]
            try:
                results = self.ocr.recognize(crop)
            except Exception as exc:
                issues.append(TacticIssue(
                    "formationTileOcrFailed",
                    f"{phase.value} tile {index} OCR failed: {exc}",
                ))
                results = []
            x = ((left + right) / 2) / width
            y = ((top + bottom) / 2) / height
            slot, slotIssues = self._slotBuild(results, phase, x, y, sourceImport, index)
            slots.append(slot)
            issues.extend(slotIssues)
        return slots, issues

    def _slotBuild(
        self,
        results: list[OcrResult],
        phase: TacticalPhase,
        x: float,
        y: float,
        sourceImport: str,
        index: int,
    ) -> tuple[FormationSlot, list[TacticIssue]]:
        fragments = [result.text.strip() for result in results if result.text.strip()]
        position = self.classifier.positionClassify(x, y)
        role = self._normalizedFind(fragments, self.vocabulary.roleNormalize)
        duty = self._normalizedFind(fragments, self.vocabulary.dutyNormalize)
        observedRole = role[1] if role else ""
        confidenceValues = [result.confidence for result in results if result.text.strip()]
        confidence = sum(confidenceValues) / len(confidenceValues) if confidenceValues else 0.0
        used = {value.casefold() for value in (observedRole, duty[1] if duty else "") if value}
        player = next(
            (
                value
                for value in fragments
                if value.casefold() not in used and not self._positionLike(value)
            ),
            None,
        )
        issues: list[TacticIssue] = []
        if position is None:
            issues.append(TacticIssue(
                "unresolvedPosition",
                f"Tile {index} is outside configured pitch zones",
            ))
        if role is None:
            issues.append(TacticIssue(
                "unresolvedRole",
                f"No role was recognized for {phase.value} tile {index}",
                " ".join(fragments),
            ))
        if duty is None:
            issues.append(TacticIssue(
                "unresolvedDuty",
                f"No duty was recognized for {phase.value} tile {index}",
                " ".join(fragments),
            ))
        state = (
            ValidationState.EXTRACTED
            if position and role and duty
            else ValidationState.UNRESOLVED
        )
        return FormationSlot(
            slotId=f"{phase.value}-{index:02d}", phase=phase, position=position,
            role=role[0] if role else None, duty=duty[0] if duty else None,
            x=x, y=y, observedRole=observedRole, displayedPlayer=player,
            confidence=confidence, sourceImport=sourceImport, validationState=state,
        ), issues

    def _tilesDetect(self, pitch: np.ndarray) -> list[tuple[int, int, int, int]]:
        settings = self.configuration.get("tileDetection", {})
        gray = cv2.cvtColor(pitch, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        mask = cv2.Canny(
            gray,
            int(settings.get("cannyLow", 35)),
            int(settings.get("cannyHigh", 110)),
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        height, width = pitch.shape[:2]
        boxes = []
        for contour in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            left, top, boxWidth, boxHeight = cv2.boundingRect(contour)
            widthRatio, heightRatio = boxWidth / width, boxHeight / height
            if not float(settings.get("minimumWidth", 0.06)) <= widthRatio <= float(
                settings.get("maximumWidth", 0.32)
            ):
                continue
            if not float(settings.get("minimumHeight", 0.025)) <= heightRatio <= float(
                settings.get("maximumHeight", 0.16)
            ):
                continue
            boxes.append((left, top, left + boxWidth, top + boxHeight))
        return sorted(boxes, key=lambda box: ((box[1] + box[3]) / 2, (box[0] + box[2]) / 2))

    def _positionLike(self, value: str) -> bool:
        return self.vocabulary.positionNormalize(value).resolved

    @staticmethod
    def _normalizedFind(fragments, normalizer):
        for fragment in fragments:
            normalized = normalizer(fragment)
            if normalized.resolved:
                return normalized.value, fragment
            for token in fragment.replace("•", " ").replace("·", " ").split():
                normalized = normalizer(token)
                if normalized.resolved:
                    return normalized.value, token
        return None

    @staticmethod
    def _regionCrop(image: np.ndarray, region: dict[str, float]) -> np.ndarray:
        height, width = image.shape[:2]
        left, top = int(float(region["x"]) * width), int(float(region["y"]) * height)
        right = int((float(region["x"]) + float(region["width"])) * width)
        bottom = int((float(region["y"]) + float(region["height"])) * height)
        return image[max(0, top):min(height, bottom), max(0, left):min(width, right)]
