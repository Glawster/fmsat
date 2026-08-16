"""Tests for anchor-relative FM26 tactic layout detection."""

from __future__ import annotations

import cv2
import numpy as np

from fmsat.core.ocr import OcrResult
from fmsat.core.parser import TacticalPhase, TacticLayoutAnchor
from fmsat.tests.conftest import FakeOcr


def _configuration() -> dict:
    return {
        "anchors": {
            "enabled": True,
            "minimumTextMatch": 0.68,
            "tabBandYMin": 0.08,
            "tabBandYMax": 0.24,
            "instructionTabSplit": 0.30,
            "underlineBrightness": 170,
            "instructionAnchorLeftGap": 0.16,
            "instructionAnchorTopGap": 0.18,
            "instructionAnchorTabX": 0.022,
            "instructionAnchorTabY": 0.105,
            "instructionAnchorTabSeparation": 0.13,
        }
    }


def testTeamInstructionsBreadcrumbLocatesModalAndLeftUnderline() -> None:
    image = np.full((600, 900, 3), 15, dtype=np.uint8)
    cv2.rectangle(image, (100, 80), (800, 500), (120, 120, 120), 2)
    cv2.line(image, (125, 140), (245, 140), (240, 240, 240), 3)
    ocr = FakeOcr([[
        OcrResult("Squad > Tactics Planner > Team Instructions", 0.98, (120, 95, 430, 118))
    ]], suppliesGeometry=True)
    result = TacticLayoutAnchor(ocr, _configuration()).referenceExtract(image, TacticalPhase.IN_POSSESSION)
    assert result.anchored is True
    assert result.detectedPhase is TacticalPhase.IN_POSSESSION
    assert result.image.shape[0] < image.shape[0]
    assert result.image.shape[1] < image.shape[1]
    assert not result.issues


def testTeamInstructionsRightUnderlineReportsPhaseMismatch() -> None:
    image = np.full((600, 900, 3), 15, dtype=np.uint8)
    cv2.rectangle(image, (100, 80), (800, 500), (120, 120, 120), 2)
    cv2.line(image, (330, 140), (470, 140), (240, 240, 240), 3)
    ocr = FakeOcr([[OcrResult("Team Instructions", 0.98, (120, 95, 260, 118))]], suppliesGeometry=True)
    result = TacticLayoutAnchor(ocr, _configuration()).referenceExtract(image, TacticalPhase.IN_POSSESSION)
    assert result.detectedPhase is TacticalPhase.OUT_OF_POSSESSION
    assert [issue.code for issue in result.issues] == ["instructionPhaseMismatch"]


def testCroppedFormationUsesImageAsReferenceWhenBreadcrumbIsVisible() -> None:
    image = np.full((400, 700, 3), 20, dtype=np.uint8)
    ocr = FakeOcr([[OcrResult("Squad > Tactics Planner", 0.97, (10, 10, 220, 30))]], suppliesGeometry=True)
    result = TacticLayoutAnchor(ocr, _configuration()).referenceExtract(image, TacticalPhase.FORMATION)
    assert result.anchored is True
    assert result.image.shape == image.shape
    assert not result.issues


def testFormationDoesNotUseAnInteriorPanelContainingBreadcrumb() -> None:
    image = np.full((700, 1200, 3), 20, dtype=np.uint8)
    cv2.rectangle(image, (10, 5), (900, 430), (120, 120, 120), 2)
    ocr = FakeOcr([[OcrResult("Match Day > Tactics Planner", 0.97, (20, 15, 260, 38))]], suppliesGeometry=True)
    result = TacticLayoutAnchor(ocr, _configuration()).referenceExtract(image, TacticalPhase.FORMATION)
    assert result.anchored is True
    assert result.image.shape == image.shape


def testSmallInstructionBreadcrumbUsesFocusedEnlargedRetry() -> None:
    image = np.full((600, 900, 3), 15, dtype=np.uint8)
    cv2.rectangle(image, (100, 80), (800, 500), (120, 120, 120), 2)
    cv2.line(image, (125, 140), (245, 140), (240, 240, 240), 3)
    ocr = FakeOcr([[], [OcrResult("Team Instructions", 0.98, (135, 234, 915, 300))]], suppliesGeometry=True)
    result = TacticLayoutAnchor(ocr, _configuration()).referenceExtract(image, TacticalPhase.IN_POSSESSION)
    assert result.anchored is True
    assert result.detectedPhase is TacticalPhase.IN_POSSESSION
    assert not result.issues


def testInstructionPanelUsesAnchoredFallbackWhenBorderIsNotContinuous() -> None:
    image = np.full((600, 900, 3), 15, dtype=np.uint8)
    cv2.line(image, (205, 155), (325, 155), (240, 240, 240), 3)
    configuration = _configuration()
    configuration["anchors"]["instructionPanelFallback"] = {
        "inPossession": {"x": 0.20, "topOffset": 0.025, "width": 0.60, "height": 0.68}
    }
    ocr = FakeOcr([[OcrResult("Team Instructions", 0.98, (220, 110, 380, 130))]], suppliesGeometry=True)
    result = TacticLayoutAnchor(ocr, configuration).referenceExtract(image, TacticalPhase.IN_POSSESSION)
    assert result.anchored is True
    assert result.image.shape[:2] == (408, 540)
    assert result.detectedPhase is TacticalPhase.IN_POSSESSION


def testInstructionAnchorPrefersModalOverBackgroundTab() -> None:
    image = np.full((800, 1200, 3), 15, dtype=np.uint8)
    cv2.line(image, (270, 235), (410, 235), (240, 240, 240), 3)
    configuration = _configuration()
    configuration["anchors"]["instructionPanelFallback"] = {
        "inPossession": {"x": 0.20, "topOffset": 0.025, "width": 0.60, "height": 0.68}
    }
    ocr = FakeOcr([
        [
            OcrResult("Team Instructions", 0.99, (120, 80, 300, 105)),
            OcrResult("Team Instructions", 0.94, (280, 175, 460, 200)),
        ],
        [OcrResult("Team Instructions", 0.95, (390, 285, 930, 360))],
    ], suppliesGeometry=True)
    result = TacticLayoutAnchor(ocr, configuration).referenceExtract(image, TacticalPhase.IN_POSSESSION)
    assert result.anchored is True
    assert result.image.shape[0] == 544
    assert result.detectedPhase is TacticalPhase.IN_POSSESSION


def testCroppedInstructionModalUsesCompleteImageFromBreadcrumb() -> None:
    """Regression for the supplied 1505x895 FM26 In Possession capture."""

    image = np.full((895, 1505, 3), 15, dtype=np.uint8)
    cv2.line(image, (17, 153), (210, 153), (240, 240, 240), 2)
    configuration = _configuration()
    configuration["anchors"]["instructionPanelFallback"] = {
        "inPossession": {"x": 0.205, "topOffset": 0.025, "width": 0.590, "height": 0.680}
    }
    # Deliberately omit tab-label OCR: the Team Instructions breadcrumb itself
    # proves this image is already the modal and prevents a destructive recrop.
    ocr = FakeOcr([[OcrResult(
        "Squad > Tactics Planner > Team Instructions", 0.99, (20, 31, 385, 52)
    )]], suppliesGeometry=True)
    result = TacticLayoutAnchor(ocr, configuration).referenceExtract(image, TacticalPhase.IN_POSSESSION)
    assert result.anchored is True
    assert result.image.shape == image.shape
    assert result.detectedPhase is TacticalPhase.IN_POSSESSION
    assert not result.issues


def testOutOfPossessionCroppedModalUsesCompleteImage() -> None:
    """Regression for the supplied shorter 1505x652 OOP modal."""

    image = np.full((652, 1505, 3), 15, dtype=np.uint8)
    cv2.line(image, (188, 130), (431, 130), (240, 240, 240), 2)
    configuration = _configuration()
    configuration["anchors"]["instructionPanelFallback"] = {
        "outOfPossession": {"x": 0.205, "topOffset": 0.025, "width": 0.590, "height": 0.490}
    }
    ocr = FakeOcr([[OcrResult(
        "Squad > Tactics Planner > Team Instructions", 0.99, (20, 31, 385, 52)
    )]], suppliesGeometry=True)
    result = TacticLayoutAnchor(ocr, configuration).referenceExtract(image, TacticalPhase.OUT_OF_POSSESSION)
    assert result.anchored is True
    assert result.image.shape == image.shape
    assert result.detectedPhase is TacticalPhase.OUT_OF_POSSESSION
    assert not result.issues
