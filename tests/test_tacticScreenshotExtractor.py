"""Tests for extracting structured tactic data from saved screenshot captures."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from fmsat.core.builder.tacticScreenshotExtractor import TacticScreenshotExtractor
from fmsat.core.detection import ScreenType
from fmsat.database import Database, StructuredTacticDefinition, Tactic


def testExtractorCreatesStructuredRowsFromSavedScreenshots(tmp_path) -> None:
    """Screenshot-only tactics should gain structured rows after extraction."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    for screenType in (
        ScreenType.TACTIC_FORMATION,
        ScreenType.TACTIC_IN_POSSESSION,
        ScreenType.TACTIC_OUT_OF_POSSESSION,
    ):
        database.tacticImportSave(f"/captures/{screenType.value}.png", screenType, "High Press")

    extractor = TacticScreenshotExtractor(database.engine)
    result = extractor.tacticExtract("High Press")

    assert result.structuredCreated is True
    assert result.complete is True
    assert result.screenshotCount == 3

    with Session(database.engine) as session:
        tactic = session.scalar(
            select(Tactic)
            .where(Tactic.normalizedName == "high press")
            .options(
                selectinload(Tactic.structuredDefinition).selectinload(
                    StructuredTacticDefinition.slots
                ),
                selectinload(Tactic.structuredDefinition).selectinload(
                    StructuredTacticDefinition.instructions
                ),
                selectinload(Tactic.structuredDefinition).selectinload(
                    StructuredTacticDefinition.issues
                ),
            )
        )
        assert tactic is not None
        assert tactic.structuredDefinition is not None
        assert len(tactic.structuredDefinition.slots) == 33
        assert len(tactic.structuredDefinition.instructions) > 0
        assert tactic.structuredDefinition.issues


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

    extractor = TacticScreenshotExtractor(database.engine)
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
                    StructuredTacticDefinition.slots
                ),
                selectinload(Tactic.structuredDefinition).selectinload(
                    StructuredTacticDefinition.instructions
                ),
            )
        )
        assert tactic is not None
        assert tactic.structuredDefinition is not None
        assert len(tactic.structuredDefinition.slots) == 33
        assert len(tactic.structuredDefinition.instructions) > 0
