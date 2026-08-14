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
            "tabBandYMax": 0.20,
            "instructionTabSplit": 0.30,
            "underlineBrightness": 170,
        }
    }


def testTeamInstructionsBreadcrumbLocatesModalAndLeftUnderline() -> None:
    image = np.full((600, 900, 3), 15, dtype=np.uint8)
    cv2.rectangle(image, (100, 80), (800, 500), (120, 120, 120), 2)
    cv2.line(image, (125, 140), (245, 140), (240, 240, 240), 3)
    ocr = FakeOcr([[
        OcrResult(
            "Squad > Tactics Planner > Team Instructions",
            0.98,
            (120, 95, 430, 118),
        )
    ]], suppliesGeometry=True)

    result = TacticLayoutAnchor(ocr, _configuration()).referenceExtract(
        image, TacticalPhase.IN_POSSESSION
    )

    assert result.anchored is True
    assert result.detectedPhase is TacticalPhase.IN_POSSESSION
    assert result.image.shape[0] < image.shape[0]
    assert result.image.shape[1] < image.shape[1]
    assert not result.issues


def testTeamInstructionsRightUnderlineReportsPhaseMismatch() -> None:
    image = np.full((600, 900, 3), 15, dtype=np.uint8)
    cv2.rectangle(image, (100, 80), (800, 500), (120, 120, 120), 2)
    cv2.line(image, (330, 140), (470, 140), (240, 240, 240), 3)
    ocr = FakeOcr([[
        OcrResult("Team Instructions", 0.98, (120, 95, 260, 118)),
    ]], suppliesGeometry=True)

    result = TacticLayoutAnchor(ocr, _configuration()).referenceExtract(
        image, TacticalPhase.IN_POSSESSION
    )

    assert result.detectedPhase is TacticalPhase.OUT_OF_POSSESSION
    assert [issue.code for issue in result.issues] == ["instructionPhaseMismatch"]


def testCroppedFormationUsesImageAsReferenceWhenBreadcrumbIsVisible() -> None:
    image = np.full((400, 700, 3), 20, dtype=np.uint8)
    ocr = FakeOcr([[
        OcrResult("Squad > Tactics Planner", 0.97, (10, 10, 220, 30)),
    ]], suppliesGeometry=True)

    result = TacticLayoutAnchor(ocr, _configuration()).referenceExtract(
        image, TacticalPhase.FORMATION
    )

    assert result.anchored is True
    assert result.image.shape == image.shape
    assert not result.issues
