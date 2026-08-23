"""Persistence tests for the squad's currently selected tactic."""

from fmsat.core.detection import ScreenType
from fmsat.core.parser import ExtractedPlayer
from fmsat.database import Database


def testMostRecentlyAppliedTacticIsRestoredFirst(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    database.squadImportSave(
        "squad.png",
        [ExtractedPlayer("Jo Example", "D (C)", "3", "4", {}, 0.98)],
        "First Team",
    )
    database.tacticImportSave(
        "one.png",
        ScreenType.TACTIC_FORMATION,
        "High Press",
    )
    database.tacticImportSave(
        "two.png",
        ScreenType.TACTIC_FORMATION,
        "Mid Block",
    )

    database.tacticApplyToSquad("First Team", "High Press")
    database.tacticApplyToSquad("First Team", "Mid Block")

    assert database.squadAppliedTactics("First Team") == (
        "Mid Block",
        "High Press",
    )

    # Re-selecting an existing application must persist it as current rather than
    # creating a duplicate relationship.
    database.tacticApplyToSquad("First Team", "High Press")

    assert database.squadAppliedTactics("First Team") == (
        "High Press",
        "Mid Block",
    )
