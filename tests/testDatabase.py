"""SQLite persistence tests."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fmsat.core.detection import ScreenType
from fmsat.core.parser import ExtractedPlayer
from fmsat.database import AttributeSnapshot, Database, Player, Tactic, TacticScreenshot


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
