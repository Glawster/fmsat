"""Tests for selected-only tactic instruction extraction."""

from __future__ import annotations

import numpy as np

from fmsat.core.ocr import OcrResult
from fmsat.core.parser import TacticalPhase, TacticInstructionExtractor, TacticVocabulary
from fmsat.tests.conftest import FakeOcr


def _configuration():
    return {
        "selection": {
            "minimumSaturation": 45,
            "minimumScore": 0.25,
            "minimumMargin": 0.12,
            "padding": 2,
        },
        "instructionRegions": {
            "inPossession": {
                "tempo": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
            }
        },
    }


def testInstructionExtractorPersistsOnlyVisiblySelectedValue() -> None:
    image = np.full((100, 200, 3), 35, dtype=np.uint8)
    image[10:40, 10:90] = (180, 20, 180)
    ocr = FakeOcr([[
        OcrResult("Higher", 0.96, (15, 15, 75, 35)),
        OcrResult("Standard", 0.99, (110, 60, 180, 80)),
    ]], suppliesGeometry=True)

    result = TacticInstructionExtractor(
        ocr, TacticVocabulary(), _configuration()
    ).instructionsExtract(image, TacticalPhase.IN_POSSESSION, "ip.png")

    assert len(result.instructions) == 1
    assert result.instructions[0].category == "tempo"
    assert result.instructions[0].value == "higher"
    assert result.instructions[0].displayValue == "Higher"
    assert not result.issues


def testInstructionExtractorReportsMissingAndAmbiguousSelectedEvidence() -> None:
    image = np.full((100, 200, 3), (180, 20, 180), dtype=np.uint8)
    ambiguous = FakeOcr([[
        OcrResult("Higher", 0.96, (10, 10, 70, 30)),
        OcrResult("Lower", 0.96, (100, 10, 160, 30)),
    ]], suppliesGeometry=True)
    missing = FakeOcr([[]], suppliesGeometry=True)

    ambiguousResult = TacticInstructionExtractor(
        ambiguous, TacticVocabulary(), _configuration()
    ).instructionsExtract(image, TacticalPhase.IN_POSSESSION, "ip.png")
    missingResult = TacticInstructionExtractor(
        missing, TacticVocabulary(), _configuration()
    ).instructionsExtract(image, TacticalPhase.IN_POSSESSION, "ip.png")

    assert ambiguousResult.instructions == ()
    assert ambiguousResult.issues[0].code == "ambiguousInstructionEvidence"
    assert missingResult.instructions == ()
    assert missingResult.issues[0].code == "missingInstructionEvidence"


def testInstructionExtractorChoosesOnlyClearlyDominantOptionRow() -> None:
    """Small coloured controls on other rows must not create three selections."""

    image = np.full((120, 200, 3), 35, dtype=np.uint8)
    image[8:34, :] = (180, 20, 180)
    image[48:74, :55] = (180, 20, 180)
    image[88:114, :60] = (180, 20, 180)
    ocr = FakeOcr([[
        OcrResult("Stay On Feet", 0.96, (40, 10, 150, 30)),
        OcrResult("Balanced", 0.98, (55, 50, 145, 70)),
        OcrResult("Get Stuck In", 0.97, (40, 90, 155, 110)),
    ]], suppliesGeometry=True)
    configuration = _configuration()
    configuration["instructionRegions"]["outOfPossession"] = {
        "tackling": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
    }

    result = TacticInstructionExtractor(
        ocr, TacticVocabulary(), configuration
    ).instructionsExtract(image, TacticalPhase.OUT_OF_POSSESSION, "oop.png")

    assert len(result.instructions) == 1
    assert result.instructions[0].category == "tackling"
    assert result.instructions[0].value == "stay on feet"
    assert not result.issues


def testInstructionExtractorPreservesUnknownSelectedTextAsIssue() -> None:
    image = np.full((100, 200, 3), (180, 20, 180), dtype=np.uint8)
    ocr = FakeOcr([[
        OcrResult("Unrecognized Tempo", 0.97, (10, 10, 150, 30)),
    ]], suppliesGeometry=True)

    result = TacticInstructionExtractor(
        ocr, TacticVocabulary(), _configuration()
    ).instructionsExtract(image, TacticalPhase.IN_POSSESSION, "ip.png")

    assert result.instructions == ()
    assert result.issues[0].code == "unknownInstructionValue"
    assert result.issues[0].observedText == "Unrecognized Tempo"
