"""Tests for extracting structured tactic data from saved screenshot captures."""

from __future__ import annotations

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from fmsat.core.builder.tacticScreenshotExtractor import TacticScreenshotExtractor
from fmsat.core.detection import ScreenType
from fmsat.core.ocr import OcrEngine, OcrResult
from fmsat.database import Database, ScreenshotDerivedTacticDefinition, Tactic


class FakeOcr(OcrEngine):
    """Return stable Formation-screen text without loading an OCR model."""

    def recognize(self, image: np.ndarray) -> list[OcrResult]:
        return [
            OcrResult("CUSTOM 4-2-3-1 DM AM Wide", 0.98),
            OcrResult("Positive", 0.99),
        ]


def _screenshotWrite(path) -> None:
    """Create a decodable stand-in image for extractor tests."""

    assert cv2.imwrite(str(path), np.zeros((40, 80, 3), dtype=np.uint8))


def testExtractorPersistsOnlyObservedValuesFromSavedScreenshots(tmp_path) -> None:
    """Unsupported slot and instruction extraction must remain unresolved."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    formationPath = tmp_path / "formation.png"
    _screenshotWrite(formationPath)
    for screenType in (
        ScreenType.TACTIC_FORMATION,
        ScreenType.TACTIC_IN_POSSESSION,
        ScreenType.TACTIC_OUT_OF_POSSESSION,
    ):
        imagePath = (
            formationPath if screenType is ScreenType.TACTIC_FORMATION else tmp_path / "x.png"
        )
        database.tacticImportSave(str(imagePath), screenType, "High Press")

    extractor = TacticScreenshotExtractor(database.engine, FakeOcr())
    result = extractor.tacticExtract("High Press")

    assert result.structuredCreated is True
    assert result.complete is False
    assert result.screenshotCount == 3

    with Session(database.engine) as session:
        tactic = session.scalar(
            select(Tactic)
            .where(Tactic.normalizedName == "high press")
            .options(
                selectinload(Tactic.structuredDefinition).selectinload(
                    ScreenshotDerivedTacticDefinition.slots
                ),
                selectinload(Tactic.structuredDefinition).selectinload(
                    ScreenshotDerivedTacticDefinition.instructions
                ),
                selectinload(Tactic.structuredDefinition).selectinload(
                    ScreenshotDerivedTacticDefinition.issues
                ),
            )
        )
        assert tactic is not None
        assert tactic.structuredDefinition is not None
        assert tactic.structuredDefinition.slots == []
        assert tactic.structuredDefinition.instructions == []
        issueCodes = {issue.code for issue in tactic.structuredDefinition.issues}
        assert "layoutAnchorUnavailable" in issueCodes
        assert "instructionImageUnavailable" in issueCodes
        assert "templateExtraction" not in issueCodes
        assert tactic.structuredDefinition.tacticMetadata["formationName"] == (
            "4-2-3-1 DM AM Wide"
        )
        assert tactic.structuredDefinition.tacticMetadata["mentality"] == "positive"


def testExtractorReturnsNotCreatedWhenNoSavedScreenshots(tmp_path) -> None:
    """Extraction should fail safely for tactics without screenshot captures."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()

    extractor = TacticScreenshotExtractor(database.engine)
    result = extractor.tacticExtract("Unknown")

    assert result.structuredCreated is False
    assert "not found" in result.message.casefold()


def testExtractorCanReplaceExistingStructuredRows(tmp_path) -> None:
    """Repeated extraction should replace rows without unique-key conflicts."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    for screenType in (
        ScreenType.TACTIC_FORMATION,
        ScreenType.TACTIC_IN_POSSESSION,
        ScreenType.TACTIC_OUT_OF_POSSESSION,
    ):
        database.tacticImportSave(f"/captures/{screenType.value}.png", screenType, "High Press")

    extractor = TacticScreenshotExtractor(database.engine, FakeOcr())
    first = extractor.tacticExtract("High Press")
    second = extractor.tacticExtract("High Press")

    assert first.structuredCreated is True
    assert second.structuredCreated is True

    with Session(database.engine) as session:
        tactic = session.scalar(
            select(Tactic)
            .where(Tactic.normalizedName == "high press")
            .options(
                selectinload(Tactic.structuredDefinition).selectinload(
                    ScreenshotDerivedTacticDefinition.slots
                ),
                selectinload(Tactic.structuredDefinition).selectinload(
                    ScreenshotDerivedTacticDefinition.instructions
                ),
            )
        )
        assert tactic is not None
        assert tactic.structuredDefinition is not None
        assert tactic.structuredDefinition.slots == []
        assert tactic.structuredDefinition.instructions == []
