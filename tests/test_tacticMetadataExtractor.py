"""Tests for Formation-screen tactic metadata extraction."""

from __future__ import annotations

import cv2
import numpy as np

from fmsat.core.builder.tacticMetadataExtractor import TacticMetadataExtractor
from fmsat.core.ocr import OcrEngine, OcrResult


class FakeOcr(OcrEngine):
    """Return configured OCR fragments for metadata parsing tests."""

    def __init__(self, texts: tuple[str, ...]) -> None:
        self.texts = texts

    def recognize(self, image: np.ndarray) -> list[OcrResult]:
        return [OcrResult(text, 0.95) for text in self.texts]


def _imageWrite(path) -> None:
    """Write a minimal valid image accepted by OpenCV."""

    assert cv2.imwrite(str(path), np.zeros((40, 80, 3), dtype=np.uint8))


def testMetadataExtractReadsFormationAndMentality(tmp_path) -> None:
    """The displayed formation notation and mentality should be canonicalized."""

    imagePath = tmp_path / "formation.png"
    _imageWrite(imagePath)
    extractor = TacticMetadataExtractor(
        FakeOcr(("CUSTOM 4 \u2013 2 \u2013 3 \u2013 1 DM AM Wide", "Positive Mentality"))
    )

    result = extractor.metadataExtract(str(imagePath))

    assert result.metadata == {
        "formationName": "4-2-3-1 DM AM Wide",
        "mentality": "positive",
    }
    assert result.issues == ()


def testMetadataExtractReportsFieldsMissingFromRecognizedText(tmp_path) -> None:
    """Unreadable metadata should remain absent and produce review evidence."""

    imagePath = tmp_path / "formation.png"
    _imageWrite(imagePath)
    extractor = TacticMetadataExtractor(FakeOcr(("Tactics", "With The Ball")))

    result = extractor.metadataExtract(str(imagePath))

    assert result.metadata == {}
    assert "formation name and mentality" in result.issues[0]


def testMetadataExtractHandlesUnavailableScreenshot(tmp_path) -> None:
    """A missing persisted screenshot should fail safely without invoking OCR."""

    extractor = TacticMetadataExtractor(FakeOcr(()))

    result = extractor.metadataExtract(str(tmp_path / "missing.png"))

    assert result.metadata == {}
    assert "unavailable" in result.issues[0]
