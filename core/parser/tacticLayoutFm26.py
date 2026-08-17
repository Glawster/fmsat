"""FM26-specific refinements for tactic layout recognition."""

from __future__ import annotations

import cv2
import numpy as np

from .tacticLayout import TacticLayoutAnchor as _BaseTacticLayoutAnchor
from .tacticModels import TacticalPhase


class TacticLayoutAnchor(_BaseTacticLayoutAnchor):
    """Retain anchor geometry while making active-tab recognition more tolerant."""

    def _activePhaseDetect(self, panel: np.ndarray) -> TacticalPhase | None:
        detected = super()._activePhaseDetect(panel)
        if detected is not None:
            return detected
        return self._activePhaseDetectFromThinUnderline(panel)

    def _activePhaseDetectFromThinUnderline(
        self,
        panel: np.ndarray,
    ) -> TacticalPhase | None:
        """Recover FM's thin active-tab underline when morphology removes it.

        Some FM26 captures render the underline as a two-pixel anti-aliased rule.
        The normal horizontal opening is intentionally strict and can erase that
        rule. This fallback searches the same configured tab band for long, thin
        bright components and classifies only their horizontal centre.
        """

        height, width = panel.shape[:2]
        settings = self.configuration.get("anchors", {})
        top = int(height * float(settings.get("tabBandYMin", 0.08)))
        bottom = int(height * float(settings.get("tabBandYMax", 0.24)))
        band = panel[max(0, top):min(height, bottom)]
        if band.size == 0:
            return None

        gray = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
        threshold = max(135, int(settings.get("underlineBrightness", 170)) - 30)
        _, bright = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        closed = cv2.morphologyEx(
            bright,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_RECT, (9, 1)),
        )

        candidates: list[tuple[int, float]] = []
        for contour in cv2.findContours(
            closed,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )[0]:
            left, _lineTop, lineWidth, lineHeight = cv2.boundingRect(contour)
            widthRatio = lineWidth / max(1, width)
            if widthRatio < 0.055 or widthRatio > 0.28:
                continue
            if lineHeight > max(7, band.shape[0] // 10):
                continue
            candidates.append((lineWidth, left + lineWidth / 2))

        if not candidates:
            return None
        center = max(candidates)[1] / max(1, width)
        split = float(settings.get("instructionTabSplit", 0.18))
        return (
            TacticalPhase.IN_POSSESSION
            if center < split
            else TacticalPhase.OUT_OF_POSSESSION
        )
