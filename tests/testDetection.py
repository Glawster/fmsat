"""Screen detector tests."""

import numpy as np

from fmsat.core.detection import KeywordScreenDetector, ScreenType
from fmsat.core.ocr import OcrResult
from fmsat.tests.conftest import FakeOcr


def testDetectsSquadAttributesFromConfiguredKeywords() -> None:
    detector = KeywordScreenDetector(
        FakeOcr([[OcrResult("Squad Attributes", 0.99), OcrResult("Name", 0.98)]]),
        ["Squad", "Attributes", "Name", "Position"],
    )

    assert detector.detect(np.zeros((100, 100, 3), dtype=np.uint8)) is ScreenType.SQUAD_ATTRIBUTES


def testUnknownWhenKeywordEvidenceIsInsufficient() -> None:
    detector = KeywordScreenDetector(
        FakeOcr([[OcrResult("Tactics", 0.99)]]),
        ["Squad", "Attributes", "Name", "Position"],
    )

    assert detector.detect(np.zeros((100, 100, 3), dtype=np.uint8)) is ScreenType.UNKNOWN
