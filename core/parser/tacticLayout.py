"""Anchor-relative FM26 tactic screenshot layout detection."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import cv2
import numpy as np

from fmsat.core.logUtils import getLogger
from fmsat.core.ocr import OcrEngine, OcrResult

from .tacticModels import TacticalPhase, TacticIssue

logger = getLogger()


@dataclass(frozen=True, slots=True)
class TacticLayoutResult:
    """A detected reference frame and any layout-validation findings."""

    image: np.ndarray
    issues: tuple[TacticIssue, ...] = ()
    detectedPhase: TacticalPhase | None = None
    anchored: bool = False


class TacticLayoutAnchor:
    """Locate FM tactic content from stable breadcrumbs and active-tab underline."""

    def __init__(self, ocr: OcrEngine, configuration: dict[str, Any]) -> None:
        self.ocr = ocr
        self.configuration = configuration

    def referenceExtract(self, image: np.ndarray, expectedPhase: TacticalPhase) -> TacticLayoutResult:
        """Return the tactic window or instructions modal as a local reference image."""

        settings = self.configuration.get("anchors", {})
        if not settings.get("enabled", False):
            return TacticLayoutResult(image)
        try:
            results = [result for result in self.ocr.recognize(image) if result.bounds]
        except Exception as exc:
            return TacticLayoutResult(image, (
                TacticIssue("layoutAnchorOcrFailed", f"Layout anchor OCR failed: {exc}"),
            ))

        phrase = "team instructions" if expectedPhase in {
            TacticalPhase.IN_POSSESSION, TacticalPhase.OUT_OF_POSSESSION
        } else "tactics planner"
        focusedResults: list[OcrResult] = []
        if expectedPhase is not TacticalPhase.FORMATION:
            focusedResults = self._focusedRecognize(image, expectedPhase)
            results.extend(focusedResults)

        anchor = self._anchorFind(results, phrase)
        if anchor is None and phrase == "tactics planner":
            anchor = self._anchorFind(results, "tactic planner")
        if anchor is None:
            anchor = self._anchorFind(focusedResults, phrase)
            if anchor is None and phrase == "tactics planner":
                anchor = self._anchorFind(focusedResults, "tactic planner")
        if anchor is None:
            logger.info(f"layout anchor not found: {phrase}")
            return TacticLayoutResult(image, (
                TacticIssue("layoutAnchorUnavailable", f"Could not locate the {phrase!r} breadcrumb"),
            ))

        if expectedPhase is TacticalPhase.FORMATION:
            logger.info(f"layout anchor={anchor.text!r} using complete Formation capture")
            return TacticLayoutResult(image, anchored=True)

        # A Team Instructions breadcrumb close to the image's top-left corner
        # proves that the capture is already the modal reference frame. Do not
        # crop it again: doing so displaced every card by roughly one column in
        # the 1505px regression captures.
        panel = self._croppedInstructionPanel(image, anchor.bounds)
        referenceMode = "cropped modal"
        if panel is None:
            panel = self._instructionPanelFromAnchors(image, results, anchor.bounds)
            referenceMode = "tab anchors"
        if panel is None:
            panel = self._containingPanel(image, anchor.bounds, expectedPhase)
            referenceMode = "contour/fallback"
        if panel is None:
            return TacticLayoutResult(image, (
                TacticIssue(
                    "layoutPanelUnavailable",
                    f"Could not locate the panel containing {anchor.text!r}",
                    anchor.text,
                ),
            ))

        left, top, right, bottom = panel
        reference = image[top:bottom, left:right]
        detectedPhase = self._activePhaseDetect(reference)
        issues: list[TacticIssue] = []
        if detectedPhase is None:
            issues.append(TacticIssue(
                "activeInstructionTabUnresolved",
                "Could not determine which Team Instructions tab is underlined",
            ))
        elif detectedPhase is not expectedPhase:
            issues.append(TacticIssue(
                "instructionPhaseMismatch",
                f"Expected {expectedPhase.value}, but the underline indicates {detectedPhase.value}",
            ))
        logger.info(
            f"layout anchor={anchor.text!r} panel=({left},{top})-({right},{bottom}) "
            f"mode={referenceMode} phase={detectedPhase.value if detectedPhase else 'unresolved'}"
        )
        return TacticLayoutResult(reference, tuple(issues), detectedPhase, True)

    @staticmethod
    def _croppedInstructionPanel(
        image: np.ndarray,
        breadcrumbBounds: tuple[float, float, float, float] | None,
    ) -> tuple[int, int, int, int] | None:
        """Use the complete image when it is already cropped to the FM modal."""

        if breadcrumbBounds is None:
            return None
        height, width = image.shape[:2]
        left, top, _right, bottom = breadcrumbBounds
        if left / max(1, width) <= 0.06 and top / max(1, height) <= 0.10 and bottom / max(1, height) <= 0.16:
            return 0, 0, width, height
        return None

    def _focusedRecognize(self, image: np.ndarray, phase: TacticalPhase) -> list[OcrResult]:
        """Retry small breadcrumb text in an enlarged, phase-specific upper crop."""

        if phase is TacticalPhase.FORMATION:
            return []
        settings = self.configuration.get("anchors", {})
        focus = settings.get("instructionBreadcrumbRegion", {})
        height, width = image.shape[:2]
        left = int(width * float(focus.get("x", 0.15)))
        top = int(height * float(focus.get("y", 0.12)))
        right = int(width * (float(focus.get("x", 0.15)) + float(focus.get("width", 0.70))))
        bottom = int(height * (float(focus.get("y", 0.12)) + float(focus.get("height", 0.24))))
        crop = image[max(0, top):min(height, bottom), max(0, left):min(width, right)]
        if crop.size == 0:
            return []
        scale = float(settings.get("instructionBreadcrumbScale", 3.0))
        enlarged = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        try:
            recognized = self.ocr.recognize(enlarged)
        except Exception:
            logger.exception("focused instruction breadcrumb OCR failed")
            return []
        transformed: list[OcrResult] = []
        for result in recognized:
            if result.bounds is None:
                continue
            x1, y1, x2, y2 = result.bounds
            transformed.append(OcrResult(
                result.text,
                result.confidence,
                (left + x1 / scale, top + y1 / scale, left + x2 / scale, top + y2 / scale),
            ))
        logger.info(
            "focused breadcrumb OCR region="
            f"({left},{top})-({right},{bottom}) scale={scale:.1f} "
            f"text={', '.join(item.text for item in transformed) or 'none'}"
        )
        return transformed

    def _anchorFind(self, results: list[OcrResult], phrase: str) -> OcrResult | None:
        minimum = float(self.configuration.get("anchors", {}).get("minimumTextMatch", 0.68))
        candidates: list[tuple[int, float, float, OcrResult]] = []
        for result in results:
            text = self._textNormalize(result.text)
            score = SequenceMatcher(None, phrase, text).ratio()
            if phrase in text:
                score = 1.0
            elif all(word in text for word in phrase.split()):
                score = max(score, 0.92)
            if score >= minimum:
                context = int("tactics planner" in text or "tactic planner" in text)
                vertical = result.center[1] if result.center is not None else 0.0
                candidates.append((context, vertical, score, result))
        if not candidates:
            return None
        return max(candidates, key=lambda item: (item[1], item[0], item[2], item[3].confidence))[3]

    def _instructionPanelFromAnchors(
        self,
        image: np.ndarray,
        results: list[OcrResult],
        breadcrumbBounds: tuple[float, float, float, float] | None,
    ) -> tuple[int, int, int, int] | None:
        """Derive the instruction reference frame from breadcrumb and tab labels."""

        if breadcrumbBounds is None:
            return None
        inPossession = self._anchorFind(results, "in possession")
        outOfPossession = self._anchorFind(results, "out of possession")
        if inPossession is None or outOfPossession is None:
            return None
        if inPossession.bounds is None or outOfPossession.bounds is None:
            return None
        breadcrumbBottom = breadcrumbBounds[3]
        inLeft, inTop, inRight, inBottom = inPossession.bounds
        outLeft, outTop, outRight, outBottom = outOfPossession.bounds
        tabHeight = max(inBottom - inTop, outBottom - outTop, 1.0)
        if min(inTop, outTop) <= breadcrumbBottom:
            return None
        if abs((inTop + inBottom) / 2 - (outTop + outBottom) / 2) > tabHeight * 1.5:
            return None
        if outLeft <= inLeft:
            return None

        settings = self.configuration.get("anchors", {})
        height, width = image.shape[:2]
        tabGap = max(outLeft - inLeft, inRight - inLeft, outRight - outLeft)
        left = int(max(0, inLeft - tabGap * float(settings.get("instructionAnchorLeftGap", 0.08))))
        top = int(max(0, breadcrumbBounds[1] - tabGap * float(settings.get("instructionAnchorTopGap", 0.18))))
        tabX = float(settings.get("instructionAnchorTabX", 0.022))
        tabY = float(settings.get("instructionAnchorTabY", 0.105))
        estimatedWidth = (inLeft - left) / tabX if tabX > 0 else width
        estimatedHeight = (inTop - top) / tabY if tabY > 0 else height
        if estimatedWidth <= 0 or estimatedHeight <= 0:
            return None
        right = int(min(width, left + estimatedWidth))
        bottom = int(min(height, top + estimatedHeight))
        tabSeparation = outLeft - inLeft
        separationRatio = float(settings.get("instructionAnchorTabSeparation", 0.13))
        if separationRatio > 0:
            right = int(min(width, left + tabSeparation / separationRatio))
        if right - left < width * 0.45 or bottom - top < height * 0.45:
            return None
        return left, top, right, bottom

    def _containingPanel(
        self,
        image: np.ndarray,
        bounds: tuple[int, int, int, int] | None,
        phase: TacticalPhase,
    ) -> tuple[int, int, int, int] | None:
        if bounds is None:
            return None
        height, width = image.shape[:2]
        centerX = (bounds[0] + bounds[2]) / 2
        centerY = (bounds[1] + bounds[3]) / 2
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        edges = cv2.morphologyEx(
            edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5))
        )
        minimumWidth = 0.35 if phase is TacticalPhase.FORMATION else 0.30
        minimumHeight = 0.45 if phase is TacticalPhase.FORMATION else 0.30
        candidates = []
        for contour in cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0]:
            left, top, boxWidth, boxHeight = cv2.boundingRect(contour)
            right, bottom = left + boxWidth, top + boxHeight
            if not (left <= centerX <= right and top <= centerY <= bottom):
                continue
            if boxWidth / width < minimumWidth or boxHeight / height < minimumHeight:
                continue
            candidates.append((boxWidth * boxHeight, (left, top, right, bottom)))
        if candidates:
            return min(candidates, key=lambda item: item[0])[1]
        if phase is TacticalPhase.FORMATION:
            return 0, 0, width, height
        return self._instructionPanelFallback(image, bounds, phase)

    def _instructionPanelFallback(
        self,
        image: np.ndarray,
        anchorBounds: tuple[int, int, int, int],
        phase: TacticalPhase,
    ) -> tuple[int, int, int, int] | None:
        """Estimate the FM modal only when the stronger anchors are absent."""

        settings = self.configuration.get("anchors", {})
        profile = settings.get("instructionPanelFallback", {}).get(phase.value, {})
        if not profile:
            return None
        height, width = image.shape[:2]
        left = int(width * float(profile.get("x", 0.205)))
        top = int(anchorBounds[1] - height * float(profile.get("topOffset", 0.025)))
        right = left + int(width * float(profile.get("width", 0.59)))
        bottom = top + int(height * float(profile.get("height", 0.68)))
        panel = (max(0, left), max(0, top), min(width, right), min(height, bottom))
        if panel[2] <= panel[0] or panel[3] <= panel[1]:
            return None
        logger.info(
            "instruction anchors unavailable; using legacy anchored fallback "
            f"({panel[0]},{panel[1]})-({panel[2]},{panel[3]})"
        )
        return panel

    def _activePhaseDetect(self, panel: np.ndarray) -> TacticalPhase | None:
        """Classify the active tab from the horizontal position of its underline."""

        height, width = panel.shape[:2]
        settings = self.configuration.get("anchors", {})
        top = int(height * float(settings.get("tabBandYMin", 0.08)))
        bottom = int(height * float(settings.get("tabBandYMax", 0.20)))
        band = panel[max(0, top):min(height, bottom)]
        if band.size == 0:
            return None
        gray = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
        _, bright = cv2.threshold(
            gray, int(settings.get("underlineBrightness", 170)), 255, cv2.THRESH_BINARY
        )
        horizontal = cv2.morphologyEx(
            bright,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, width // 30), 1)),
        )
        lines = []
        for contour in cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            left, _lineTop, lineWidth, lineHeight = cv2.boundingRect(contour)
            if lineWidth / width < 0.06 or lineHeight > max(6, band.shape[0] // 4):
                continue
            lines.append((lineWidth, left + lineWidth / 2))
        if not lines:
            return None
        center = max(lines)[1] / width
        split = float(settings.get("instructionTabSplit", 0.18))
        return TacticalPhase.IN_POSSESSION if center < split else TacticalPhase.OUT_OF_POSSESSION

    @staticmethod
    def _textNormalize(value: str) -> str:
        return " ".join(value.casefold().replace(">", " ").replace("/", " ").split())
