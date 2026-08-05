"""SQLite persistence tests."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fmsat.core.detection import ScreenType
from fmsat.core.parser import ExtractedPlayer
from fmsat.database import (
    AttributeSnapshot,
    Database,
    Player,
    Squad,
    SquadScreenshot,
    SquadTacticApplication,
    Tactic,
    TacticScreenshot,
)


def testConfirmedImportIsSavedAtomically(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    extracted = ExtractedPlayer(
        "Jo Example",
        "D (C)",
        "3",
        "4",
        {"marking": 16, "passing": 13},
        0.98,
    )

    importSession = database.importSave(
        "squad.png", ScreenType.SQUAD_ATTRIBUTES, [extracted], "High Press"
    )

    with Session(database.engine) as session:
        assert importSession.id is not None
        assert session.scalar(select(func.count()).select_from(Player)) == 1
        assert session.scalar(select(func.count()).select_from(AttributeSnapshot)) == 2
        assert session.scalar(select(func.count()).select_from(Tactic)) == 1
        assert session.scalar(select(func.count()).select_from(TacticScreenshot)) == 1
        stored = session.scalar(select(Player))
        assert stored is not None
        assert stored.name == "Jo Example"

    assert database.tacticsList() == ["High Press"]
    assert database.screenTypesForTactic("high press") == {ScreenType.SQUAD_ATTRIBUTES}


def testUpdatedScreenshotReusesTacticAndKeepsImportHistory(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    player = ExtractedPlayer("Jo Example", "D (C)", "3", "4", {}, 0.98)

    database.importSave("first.png", ScreenType.SQUAD_ATTRIBUTES, [player], "High Press")
    database.importSave("updated.png", ScreenType.SQUAD_ATTRIBUTES, [player], "HIGH PRESS")

    with Session(database.engine) as session:
        assert session.scalar(select(func.count()).select_from(Tactic)) == 1
        assert session.scalar(select(func.count()).select_from(TacticScreenshot)) == 2


def testThreeTacticScreensAreStoredWithoutPlayerRows(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()

    for screenType in (
        ScreenType.TACTIC_FORMATION,
        ScreenType.TACTIC_IN_POSSESSION,
        ScreenType.TACTIC_OUT_OF_POSSESSION,
    ):
        database.tacticImportSave(f"{screenType.value}.png", screenType, "High Press")

    with Session(database.engine) as session:
        assert session.scalar(select(func.count()).select_from(Tactic)) == 1
        assert session.scalar(select(func.count()).select_from(TacticScreenshot)) == 3
        assert session.scalar(select(func.count()).select_from(Player)) == 0

    assert database.screenTypesForTactic("High Press") == {
        ScreenType.TACTIC_FORMATION,
        ScreenType.TACTIC_IN_POSSESSION,
        ScreenType.TACTIC_OUT_OF_POSSESSION,
    }


def testSquadImportIsIndependentFromTactics(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    player = ExtractedPlayer("Jo Example", "D (C)", "3", "4", {}, 0.98)

    database.tacticImportSave("formation.png", ScreenType.TACTIC_FORMATION, "High Press")
    database.squadImportSave("squad.png", [player], "First Team")

    with Session(database.engine) as session:
        assert session.scalar(select(func.count()).select_from(Tactic)) == 1
        assert session.scalar(select(func.count()).select_from(Squad)) == 1
        assert session.scalar(select(func.count()).select_from(SquadScreenshot)) == 1
        assert session.scalar(select(func.count()).select_from(Player)) == 1
        squadCapture = session.scalar(select(SquadScreenshot))
        assert squadCapture is not None
        assert squadCapture.squad.name == "First Team"

    assert database.squadsList() == ["First Team"]
    assert database.playerNamesForSquad("first team") == {"Jo Example"}


def testPlayerNamesForSquadDoNotIncludeOtherSquads(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    database.squadImportSave(
        "first.png",
        [ExtractedPlayer("Jo Example", "D (C)", "3", "4", {}, 0.98)],
        "First Team",
    )
    database.squadImportSave(
        "youth.png",
        [ExtractedPlayer("Sam Example", "M (C)", "2", "3", {}, 0.97)],
        "Under 21s",
    )

    assert database.playerNamesForSquad("FIRST TEAM") == {"Jo Example"}
    assert database.playerNamesForSquad("Under 21s") == {"Sam Example"}
    assert database.playerNamesForSquad("Unknown") == set()


def testTacticCanBeAppliedToSquadWithoutChangingOwnership(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    player = ExtractedPlayer("Jo Example", "D (C)", "3", "4", {}, 0.98)
    database.tacticImportSave("formation.png", ScreenType.TACTIC_FORMATION, "High Press")
    database.squadImportSave("squad.png", [player], "First Team")

    first = database.tacticApplyToSquad("First Team", "High Press")
    repeated = database.tacticApplyToSquad("first team", "high press")

    assert first.id == repeated.id
    with Session(database.engine) as session:
        assert session.scalar(select(func.count()).select_from(SquadTacticApplication)) == 1
        application = session.scalar(select(SquadTacticApplication))
        assert application is not None
        assert application.squad.name == "First Team"
        assert application.tactic.name == "High Press"
