"""FM26 refinements for formation geometry and role OCR."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from fmsat.core.logUtils import getLogger
from fmsat.core.ocr import OcrResult

from .tacticFormation import TacticFormationExtractor as BaseTacticFormationExtractor
from .tacticModels import FormationSlot, TacticalPhase, TacticIssue

logger = getLogger()


class TacticFormationExtractor(BaseTacticFormationExtractor):
    """Anchor pitch depth to the visible FM field and recover short role labels."""

    def _phaseRegionsResolve(self, image: np.ndarray) -> dict[str, Any]:
        """Refine configured pitch profiles from the visible green pitch extent.

        The horizontal profile remains useful for distinguishing the compact and
        wide Planner layouts. The calibrated pitch top is deliberately preserved
        because it excludes Planner controls above the playing surface; only the
        lower pitch extent is extended from visible screenshot evidence.
        """

        configured = super()._phaseRegionsResolve(image)
        refined: dict[str, Any] = {}
        changed = False
        for phase in (TacticalPhase.IN_POSSESSION, TacticalPhase.OUT_OF_POSSESSION):
            region = configured.get(phase.value)
            if not isinstance(region, dict):
                continue
            detected = self._pitchVerticalRegionDetect(image, region)
            if detected is not None:
                refined[phase.value] = detected
                changed = True
                logger.info(
                    "formation pitch extent detected phase=%s y=%.3f height=%.3f",
                    phase.value,
                    float(detected["y"]),
                    float(detected["height"]),
                )
            else:
                refined[phase.value] = region
                logger.info(
                    "formation pitch extent unavailable phase=%s; using configured profile",
                    phase.value,
                )

        return refined if changed else configured

    @staticmethod
    def _pitchVerticalRegionDetect(
        image: np.ndarray,
        configured: dict[str, Any],
    ) -> dict[str, float] | None:
        """Extend the configured pitch region to the visible lower field edge.

        The top of the calibrated region is part of the chrome-rejection contract:
        moving it upward exposes the In Possession/Out of Possession tabs and eye
        controls to role-tile detection. Therefore visual detection may extend the
        bottom edge but must never move the configured top edge upward.
        """

        height, width = image.shape[:2]
        if height <= 0 or width <= 0:
            return None
        x = float(configured.get("x", 0.0))
        y = float(configured.get("y", 0.0))
        regionWidth = float(configured.get("width", 0.0))
        if regionWidth <= 0:
            return None

        left = max(0, int((x - 0.015) * width))
        right = min(width, int((x + regionWidth + 0.015) * width))
        configuredTop = max(0, min(height - 1, int(y * height)))
        searchStart = max(0, configuredTop - int(height * 0.03))
        if right <= left or searchStart >= height:
            return None

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        green = cv2.inRange(
            hsv,
            np.array([70, 50, 20], dtype=np.uint8),
            np.array([105, 255, 160], dtype=np.uint8),
        )
        coverage = np.mean(green[searchStart:height, left:right] > 0, axis=1)
        rows = np.flatnonzero(coverage >= 0.12)
        if rows.size == 0:
            return None

        detectedBottom = searchStart + int(rows[-1]) + 1
        detectedHeight = detectedBottom - configuredTop
        if detectedHeight < height * 0.50:
            return None
        if detectedBottom < height * 0.80:
            return None

        return {
            "x": x,
            "y": y,
            "width": regionWidth,
            "height": detectedHeight / height,
        }

    def _tilesDetect(self, pitch: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Combine conservative contour detection with FM26 role-bar recovery."""

        boxes = list(super()._tilesDetect(pitch))
        boxes.extend(self._horizontalRoleBarsDetect(pitch))
        boxes.extend(self._goalkeeperRoleBoxDetect(pitch))
        height, width = pitch.shape[:2]
        boxes = self._duplicatesRemove(boxes, width, height)
        boxes = [
            box for box in boxes if not self._excludedCandidate(box, width, height)
        ]
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
                top + max(1, boxHeight // 4):top + max(2, boxHeight * 3 // 4),
                left + max(1, boxWidth // 8):left + max(2, boxWidth * 7 // 8),
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
            return [], [TacticIssue(
                "emptyPitchRegion",
                f"Configured {phase.value} pitch region is empty",
            )]
        boxes = self._tilesDetect(pitch)
        logger.value(f"{phase.value} formation tile candidates", len(boxes))
        issues: list[TacticIssue] = []
        if not boxes:
            return [], [TacticIssue(
                "missingFormationSlots",
                f"No {phase.value} role tiles were detected",
            )]
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
                issues.append(TacticIssue(
                    "formationTileOcrFailed",
                    f"{phase.value} candidate {candidateIndex} OCR failed: {exc}",
                ))
                results = []

            # A candidate is only a formation tile when its exact coloured role
            # label contains readable text. The larger card crop can include a
            # neighbouring player's role, so it is evidence for slot details but
            # never sufficient evidence that this detected rectangle is itself a
            # role tile.
            focusedResults = self._roleLabelRecognize(pitch, box)
            if not focusedResults:
                logger.info(
                    "%s candidate %d rejected: no text inside exact role-label box",
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
            slot, slotIssues = self._slotBuild(
                results, phase, x, y, sourceImport, acceptedIndex
            )
            slots.append(slot)
            issues.extend(slotIssues)

        if not slots:
            issues.append(TacticIssue(
                "missingFormationSlots",
                f"No {phase.value} role tiles contained readable role-label text",
            ))
        return slots, issues

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
            max(0, top - padY):min(height, bottom + padY),
            max(0, left - padX):min(width, right + padX),
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
            return [
                result
                for result in self.ocr.recognize(enlarged)
                if result.text.strip()
            ]
        except Exception:
            logger.exception("focused formation role-label OCR failed")
            return []
