"""FM26 refinements for formation geometry and role OCR."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import cv2
import numpy as np

from fmsat.core.logUtils import getLogger
from fmsat.core.ocr import OcrResult

from .tacticFormation import TacticFormationExtractor as BaseTacticFormationExtractor
from .tacticModels import FormationSlot, TacticalPhase, TacticIssue

logger = getLogger()


class TacticFormationExtractor(BaseTacticFormationExtractor):
    """Recover FM26 role labels while preserving calibrated pitch geometry."""

    def _phaseRegionsResolve(self, image: np.ndarray) -> dict[str, Any]:
        """Use the calibrated Planner pitch profiles without green-panel drift.

        FM uses the same green treatment for the pitch and the substitutes panel.
        Extending a pitch crop from colour alone therefore changes normalized slot
        depth and can pull the substitutes panel into formation extraction. The
        reviewed layout profiles are the evidence for pitch geometry; role-tile
        detection may recover labels inside those bounds but must not redefine the
        pitch extent from colour.
        """

        return super()._phaseRegionsResolve(image)

    def _excludedCandidate(
        self,
        box: tuple[int, int, int, int],
        width: int,
        height: int,
    ) -> bool:
        """Keep valid central forwards even when their role bar is near pitch top.

        The historical full-width top exclusion was added for chrome from a badly
        extended crop. With calibrated pitch bounds restored, a genuine STC role
        can sit inside that shallow band. Retain the narrower eye-control exclusion
        and every other configured exclusion, but ignore only the obsolete
        full-width shallow top strip.
        """

        centerX = ((box[0] + box[2]) / 2) / width
        centerY = ((box[1] + box[3]) / 2) / height
        for region in self.configuration.get("tileDetection", {}).get("excludedRegions", []):
            xMinimum = float(region["x"])
            yMinimum = float(region["y"])
            regionWidth = float(region["width"])
            regionHeight = float(region["height"])
            if xMinimum == 0.0 and yMinimum == 0.0 and regionWidth >= 1.0 and regionHeight <= 0.06:
                continue
            if (
                xMinimum <= centerX <= xMinimum + regionWidth
                and yMinimum <= centerY <= yMinimum + regionHeight
            ):
                logger.info(
                    "formation tile candidate excluded as pitch chrome: "
                    f"center=({centerX:.3f},{centerY:.3f})"
                )
                return True
        return False

    def _tilesDetect(self, pitch: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Combine conservative contour detection with FM26 role-bar recovery."""

        boxes = list(super()._tilesDetect(pitch))
        boxes.extend(self._horizontalRoleBarsDetect(pitch))
        boxes.extend(self._goalkeeperRoleBoxDetect(pitch))
        height, width = pitch.shape[:2]
        boxes = self._duplicatesRemove(boxes, width, height)
        boxes = [box for box in boxes if not self._excludedCandidate(box, width, height)]
        return sorted(
            boxes,
            key=lambda box: ((box[1] + box[3]) / 2, (box[0] + box[2]) / 2),
        )

    def _horizontalRoleBarsDetect(
        self,
        pitch: np.ndarray,
    ) -> list[tuple[int, int, int, int]]:
        """Find long saturated FM26 role bars missed by edge-contour detection."""

        height, width = pitch.shape[:2]
        hsv = cv2.cvtColor(pitch, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        hue = hsv[:, :, 0]
        mask = ((saturation >= 90) & (value >= 70)).astype(np.uint8) * 255

        pitchGreen = (hue >= 70) & (hue <= 100) & (value < 105)
        mask[pitchGreen] = 0

        openWidth = max(15, int(width * 0.045))
        closeWidth = max(5, int(width * 0.016))
        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (openWidth, 3)),
        )
        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_RECT, (closeWidth, 3)),
        )

        boxes: list[tuple[int, int, int, int]] = []
        for contour in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            left, top, boxWidth, boxHeight = cv2.boundingRect(contour)
            widthRatio = boxWidth / max(1, width)
            heightRatio = boxHeight / max(1, height)
            aspectRatio = boxWidth / max(1, boxHeight)
            if not 0.12 <= widthRatio <= 0.35:
                continue
            if not 0.012 <= heightRatio <= 0.065:
                continue
            if aspectRatio < 3.0:
                continue
            box = (left, top, left + boxWidth, top + boxHeight)
            if self._excludedCandidate(box, width, height):
                continue
            boxes.append(box)
        return boxes

    def _goalkeeperRoleBoxDetect(
        self,
        pitch: np.ndarray,
    ) -> list[tuple[int, int, int, int]]:
        """Recover the lower-centre goalkeeper role label with relaxed geometry."""

        height, width = pitch.shape[:2]
        gray = cv2.GaussianBlur(cv2.cvtColor(pitch, cv2.COLOR_BGR2GRAY), (3, 3), 0)
        mask = cv2.Canny(gray, 35, 110)
        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3)),
        )
        hsv = cv2.cvtColor(pitch, cv2.COLOR_BGR2HSV)
        boxes: list[tuple[int, int, int, int]] = []
        for contour in cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0]:
            left, top, boxWidth, boxHeight = cv2.boundingRect(contour)
            centerX = (left + boxWidth / 2) / max(1, width)
            centerY = (top + boxHeight / 2) / max(1, height)
            if not 0.30 <= centerX <= 0.70 or centerY < 0.80:
                continue
            if not 0.12 <= boxWidth / max(1, width) <= 0.38:
                continue
            if not 0.025 <= boxHeight / max(1, height) <= 0.12:
                continue
            if boxWidth / max(1, boxHeight) < 1.6:
                continue
            inset = hsv[
                top + max(1, boxHeight // 4) : top + max(2, boxHeight * 3 // 4),
                left + max(1, boxWidth // 8) : left + max(2, boxWidth * 7 // 8),
            ]
            if inset.size == 0:
                continue
            if float(np.mean(inset[:, :, 1])) < 15:
                continue
            if float(np.mean(inset[:, :, 2])) < 70:
                continue
            boxes.append((left, top, left + boxWidth, top + boxHeight))
        return boxes

    def _phaseExtract(
        self,
        pitch: np.ndarray,
        phase: TacticalPhase,
        sourceImport: str,
        diagnostic: np.ndarray | None = None,
        diagnosticOffset: tuple[int, int] = (0, 0),
    ) -> tuple[list[FormationSlot], list[TacticIssue]]:
        if pitch.size == 0:
            return [], [
                TacticIssue(
                    "emptyPitchRegion",
                    f"Configured {phase.value} pitch region is empty",
                )
            ]
        boxes = self._tilesDetect(pitch)
        logger.value(f"{phase.value} formation tile candidates", len(boxes))
        issues: list[TacticIssue] = []
        if not boxes:
            return [], [
                TacticIssue(
                    "missingFormationSlots",
                    f"No {phase.value} role tiles were detected",
                )
            ]
        height, width = pitch.shape[:2]
        slots: list[FormationSlot] = []
        for candidateIndex, box in enumerate(boxes, start=1):
            left, top, right, bottom = box
            crop = self._tileCrop(pitch, box)
            logger.info(
                f"{phase.value} candidate {candidateIndex} label box="
                f"({left},{top})-({right},{bottom}) crop={crop.shape[1]}x{crop.shape[0]}"
            )
            try:
                results = self.ocr.recognize(crop)
            except Exception as exc:
                issues.append(
                    TacticIssue(
                        "formationTileOcrFailed",
                        f"{phase.value} candidate {candidateIndex} OCR failed: {exc}",
                    )
                )
                results = []

            focusedResults = self._roleLabelRecognize(pitch, box)
            if not focusedResults:
                logger.info(
                    "%s candidate %d rejected: no text inside exact role-label box",
                    phase.value,
                    candidateIndex,
                )
                continue
            if self._phaseChromeLabel(focusedResults):
                logger.info(
                    "%s candidate %d rejected: focused OCR is phase chrome",
                    phase.value,
                    candidateIndex,
                )
                continue

            results = [*focusedResults, *results]
            logger.info(
                f"{phase.value} candidate {candidateIndex} focused role OCR: "
                f"{', '.join(result.text for result in focusedResults)}"
            )

            acceptedIndex = len(slots) + 1
            if diagnostic is not None:
                offsetX, offsetY = diagnosticOffset
                self._diagnosticBox(
                    diagnostic,
                    (left + offsetX, top + offsetY, right + offsetX, bottom + offsetY),
                    f"{phase.value} tile {acceptedIndex}",
                    (255, 0, 255),
                    2,
                )

            logger.info(
                f"{phase.value} tile {acceptedIndex} OCR: "
                f"{', '.join(result.text for result in results) or 'none'}"
            )
            x = ((left + right) / 2) / width
            y = ((top + bottom) / 2) / height
            slot, slotIssues = self._slotBuild(results, phase, x, y, sourceImport, acceptedIndex)
            focusedObservedRole = self._focusedObservedRoleFind(focusedResults)
            if not slot.observedRole and focusedObservedRole:
                slot = replace(slot, observedRole=focusedObservedRole)
            slots.append(slot)
            issues.extend(slotIssues)

        if not slots:
            issues.append(
                TacticIssue(
                    "missingFormationSlots",
                    f"No {phase.value} role tiles contained readable role-label text",
                )
            )
        return slots, issues

    @staticmethod
    def _phaseChromeLabel(results: list[OcrResult]) -> bool:
        """Identify phase-tab text from exact OCR instead of rejecting by pitch depth."""

        for result in results:
            compact = "".join(
                character for character in result.text.casefold() if character.isalnum()
            )
            if compact in {"inpossession", "outofpossession"}:
                return True
        return False

    @staticmethod
    def _focusedObservedRoleFind(results: list[OcrResult]) -> str:
        """Retain exact role-box evidence even when a token also names a position."""

        for result in results:
            token = result.text.strip().strip("()[]{}.,:;")
            if token == "GK":
                return token
        return ""

    def _roleLabelRecognize(
        self,
        pitch: np.ndarray,
        box: tuple[int, int, int, int],
    ) -> list[OcrResult]:
        """OCR only the coloured role label when the expanded player-card crop misses it."""

        left, top, right, bottom = box
        height, width = pitch.shape[:2]
        padX = max(2, int((right - left) * 0.08))
        padY = max(1, int((bottom - top) * 0.18))
        label = pitch[
            max(0, top - padY) : min(height, bottom + padY),
            max(0, left - padX) : min(width, right + padX),
        ]
        if label.size == 0:
            return []
        enlarged = cv2.resize(
            label,
            None,
            fx=6.0,
            fy=6.0,
            interpolation=cv2.INTER_CUBIC,
        )
        try:
            return [result for result in self.ocr.recognize(enlarged) if result.text.strip()]
        except Exception:
            logger.exception("focused formation role-label OCR failed")
            return []
