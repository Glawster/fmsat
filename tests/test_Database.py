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


def testPairedSquadImportPreservesBothCapturesAndOnePlayerSnapshot(tmp_path) -> None:

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    player = ExtractedPlayer("Jo Example", "D (C)", "3", "4", {"passing": 12}, 0.98)

    session = database.squadImportPairSave(
        ["attributes-one.png", "attributes-two.png"],
        [player],
        "First Team",
    )

    squad = database.squadRecords()[0]
    assert session.id > 0
    assert squad.captureCount == 2
    assert squad.playerCount == 1


def testSquadCaptureBatchPreservesEveryPageAndOnePlayerSnapshot(tmp_path) -> None:

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    player = ExtractedPlayer("Jo Example", "D (C)", "3", "4", {"passing": 12}, 0.98)

    database.squadImportBatchSave(
        ["view1-page1.png", "view1-page2.png", "view2-page1.png", "view2-page2.png"],
        [player],
        "First Team",
    )

    squad = database.squadRecords()[0]
    assert squad.captureCount == 4
    assert squad.playerCount == 1


def testSquadCaptureBatchAllowsOneScreenshotAppend(tmp_path) -> None:

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    player = ExtractedPlayer("Jo Example", "D (C)", "3", "4", {"passing": 12}, 0.98)

    session = database.squadImportBatchSave(
        ["attributes-update.png"],
        [player],
        "First Team",
    )

    squad = database.squadRecords()[0]
    assert session.id > 0
    assert squad.captureCount == 1
    assert squad.playerCount == 1


def testStoredSquadCleanupCorrectsAndMergesExactIdentityDuplicates(tmp_path) -> None:

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    database.squadImportSave(
        "first.png",
        [ExtractedPlayer("Max Power.", "Dm,m (C)", "114", "130", {"passing": 15}, 0.96)],
        "First Team",
    )
    database.squadImportSave(
        "second.png",
        [ExtractedPlayer("Max Power", "DM, M (C)", "114", "130", {"vision": 16}, 0.99)],
        "First Team",
    )

    result = database.squadClean("first team")

    assert result.correctedCount == 2
    assert result.mergedCount == 1
    assert result.ambiguousCount == 0
    assert result.remainingCount == 1
    assert database.squadRecords()[0].playerCount == 1
    with Session(database.engine) as session:
        player = session.scalar(select(Player))
        assert player is not None
        assert player.name == "Max Power"
        assert player.positions == "DM, M (C)"
        assert {item.attributeName: item.attributeValue for item in player.attributes} == {
            "passing": 15,
            "vision": 16,
        }


def testStoredSquadCleanupRetainsAmbiguousSameNamePlayers(tmp_path) -> None:

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    database.squadImportSave(
        "first.png",
        [ExtractedPlayer("Max Power", "DM", "114", "130", {}, 0.98)],
        "First Team",
    )
    database.squadImportSave(
        "second.png",
        [ExtractedPlayer("Max Power", "DM", "113", "130", {}, 0.97)],
        "First Team",
    )

    result = database.squadClean("First Team")

    assert result.mergedCount == 0
    assert result.ambiguousCount == 1
    assert result.remainingCount == 2


def testStoredSquadCleanupResolvesAndRemovesCompositeOcrRows(tmp_path) -> None:

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    trusted = [
        ExtractedPlayer("Curtis Tilt", "D (C)", "105", "120", {}, 0.98),
        ExtractedPlayer("Matthew Pennington", "D (C)", "105", "125", {}, 0.99),
        ExtractedPlayer("Jack Ryder", "DM, M (C)", "43", "81", {}, 0.98),
        ExtractedPlayer("Lewis Boney", "D/WB (L)", "65", "112", {}, 0.98),
        ExtractedPlayer("Harry Parr", "M (C), AM (LC)", "42", "95", {}, 0.98),
        ExtractedPlayer("Paul Mullin", "ST (C)", "100", "110", {}, 0.98),
        ExtractedPlayer(
            "Stephen Humphrys", "AM (RLC), ST (C)", "109", "130 120", {}, 0.98
        ),
        ExtractedPlayer("Tyreik Wright", "WB/M/AM (L)", "98", "115", {}, 0.98),
    ]
    errors = [
        ExtractedPlayer(
            "De Curtis Tilt Matthew Pennington",
            "D (C)",
            "105",
            "125",
            {},
            0.97,
        ),
        ExtractedPlayer(
            "Jack Ryder e Lewis Boney Lewis Boney",
            "D/WB (L) DM, M (C)",
            "65 43",
            "8 81 112",
            {},
            0.95,
        ),
        ExtractedPlayer("Harry Parr", "M (C), AM (LC)", "f2 42", "95", {}, 0.97),
        ExtractedPlayer(
            "Paul Mullin Stephen Humphrys",
            "AM (RLC), ST (C)",
            "107 109",
            "120 130",
            {},
            0.97,
        ),
        ExtractedPlayer("Tyrei Wright", "WB/M/AM (L)", "98", "115", {}, 0.97),
    ]
    database.squadImportSave("trusted.png", trusted, "First Team")
    database.squadImportSave("errors.png", errors, "First Team")

    result = database.squadClean("First Team")

    assert result.mergedCount == 5
    assert result.remainingCount == 8
    assert database.playerNamesForSquad("First Team") == {
        "Curtis Tilt",
        "Matthew Pennington",
        "Jack Ryder",
        "Lewis Boney",
        "Harry Parr",
        "Paul Mullin",
        "Stephen Humphrys",
        "Tyreik Wright",
    }


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


def testManagementRecordsIncludeScreenshotProvenance(tmp_path) -> None:

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    player = ExtractedPlayer("Jo Example", "D (C)", "3", "4", {}, 0.98)
    database.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "High Press",
    )
    database.squadImportSave("/captures/squad.png", [player], "First Team")
    database.squadClubImageSave("/captures/club-information.png", "First Team")

    tactic = database.tacticRecords()[0]
    squad = database.squadRecords()[0]
    storedPlayer = database.squadPlayerRecords("first team")[0]

    assert tactic.name == "High Press"
    assert tactic.captureCount == 1
    assert tactic.formationImage == "/captures/formation.png"
    assert squad.playerCount == 1
    assert squad.captureCount == 1
    assert squad.clubImage == "/captures/club-information.png"
    assert storedPlayer.name == "Jo Example"
    assert storedPlayer.imageFilename == "/captures/squad.png"


def testTacticDetailRecordIncludesCapturesAssignmentsAndLatestUpdate(tmp_path) -> None:

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    database.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "High Press",
    )
    latest = database.tacticImportSave(
        "/captures/in-possession.png",
        ScreenType.TACTIC_IN_POSSESSION,
        "HIGH PRESS",
    )
    player = ExtractedPlayer("Jo Example", "D (C)", "3", "4", {}, 0.98)
    database.squadImportSave("/captures/first-team.png", [player], "First Team")
    database.squadImportSave("/captures/under-21s.png", [player], "Under 21s")
    database.tacticApplyToSquad("Under 21s", "High Press")
    database.tacticApplyToSquad("First Team", "High Press")

    record = database.tacticDetailRecord(" high press ")

    assert record is not None
    assert record.name == "High Press"
    assert record.capturedScreenTypes == (
        ScreenType.TACTIC_FORMATION.value,
        ScreenType.TACTIC_IN_POSSESSION.value,
    )
    assert record.captureCount == 2
    assert record.assignedSquads == ("First Team", "Under 21s")
    assert record.updatedAt == latest.date


def testTacticDetailRecordReturnsNoneForUnknownTactic(tmp_path) -> None:

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()

    assert database.tacticDetailRecord("Unknown") is None


def testDeletingTacticRemovesOwnedImportsButLeavesSquad(tmp_path) -> None:

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    player = ExtractedPlayer("Jo Example", "D (C)", "3", "4", {}, 0.98)
    database.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "High Press",
    )
    database.squadImportSave("/captures/squad.png", [player], "First Team")
    database.tacticApplyToSquad("First Team", "High Press")

    deleted = database.tacticsDelete(["high press"])

    assert deleted.deletedCount == 1
    assert deleted.imageFilenames == ("/captures/formation.png",)
    assert database.tacticsList() == []
    assert database.squadsList() == ["First Team"]
    assert database.playerNamesForSquad("First Team") == {"Jo Example"}


def testBulkDeletingTacticsLeavesUncheckedTacticSquadAndRelationship(tmp_path) -> None:

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    player = ExtractedPlayer("Jo Example", "D (C)", "3", "4", {}, 0.98)
    for name in ("High Press", "Low Block", "Wing Play"):
        database.tacticImportSave(
            f"/captures/{name}.png",
            ScreenType.TACTIC_FORMATION,
            name,
        )
    database.squadImportSave("/captures/squad.png", [player], "First Team")
    database.tacticApplyToSquad("First Team", "High Press")
    database.tacticApplyToSquad("First Team", "Low Block")

    deleted = database.tacticsDelete(["high press", "wing play"])

    assert deleted.deletedCount == 2
    assert set(deleted.imageFilenames) == {
        "/captures/High Press.png",
        "/captures/Wing Play.png",
    }
    assert database.tacticsList() == ["Low Block"]
    assert database.squadsList() == ["First Team"]
    with Session(database.engine) as session:
        assert session.scalar(select(func.count()).select_from(SquadTacticApplication)) == 1


def testFormationImagePersistsAcrossDatabaseRestart(tmp_path) -> None:

    databasePath = tmp_path / "test.sqlite3"
    firstDatabase = Database(databasePath)
    firstDatabase.initialize()
    firstDatabase.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "High Press",
    )

    restartedDatabase = Database(databasePath)
    restartedDatabase.initialize()

    records = restartedDatabase.tacticRecords()
    assert len(records) == 1
    assert records[0].name == "High Press"
    assert records[0].formationImage == "/captures/formation.png"


def testDeletingSquadRemovesOwnedPlayersButLeavesTactic(tmp_path) -> None:

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    player = ExtractedPlayer("Jo Example", "D (C)", "3", "4", {}, 0.98)
    database.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "High Press",
    )
    database.squadImportSave("/captures/squad.png", [player], "First Team")
    database.squadClubImageSave("/captures/club-information.png", "First Team")
    database.tacticApplyToSquad("First Team", "High Press")

    deleted = database.squadsDelete(["FIRST TEAM"])

    assert deleted.deletedCount == 1
    assert set(deleted.imageFilenames) == {
        "/captures/squad.png",
        "/captures/club-information.png",
    }
    assert database.squadsList() == []
    assert database.tacticsList() == ["High Press"]
    assert database.playersList() == []
