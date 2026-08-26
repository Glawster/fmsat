"""Editable squad object-model persistence tests."""

from dataclasses import replace
from datetime import datetime

from fmsat.core.parser import ExtractedPlayer
from fmsat.core.squadModel import (
    SquadModel,
    SquadModelPlayer,
    SquadModelService,
    squadPlayersMerge,
)
from fmsat.database import Database


def testSquadModelRetainsKnownPlayerTraits(tmp_path) -> None:
    """Known traits must survive the editable model persistence boundary."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    service = SquadModelService(database.engine)
    model = SquadModel(
        name="First Team",
        players=(
            SquadModelPlayer(
                name="Example Player",
                positions="ST (C)",
                ca="",
                pa="",
                confidence=0.9,
                attributes=(),
                traits=("Places Shots", "Curls Ball"),
            ),
        ),
        generatedAt=datetime(2026, 8, 15),
        updatedAt=datetime(2026, 8, 15),
        evidenceSuperseded=False,
    )

    service.modelSave(model)
    loaded = service.modelLoad("First Team", create=False)

    assert loaded is not None
    assert loaded.players[0].traits == ("Curls Ball", "Places Shots")


def testModelSavePreservesPerPlayerValidationState(tmp_path) -> None:
    """Saving one corrected player must not confirm other uncertain identities."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    service = SquadModelService(database.engine)
    model = SquadModel(
        name="First Team",
        players=(
            replace(_namedPlayer("Smith, Ella"), validationState="corrected"),
            replace(_namedPlayer("Rennie, Q Sophie"), validationState="uncertain"),
        ),
        generatedAt=datetime(2026, 8, 15),
        updatedAt=datetime(2026, 8, 15),
        evidenceSuperseded=False,
    )

    service.modelSave(model)
    loaded = service.modelLoad("First Team", create=False)

    assert loaded is not None
    assert {player.name: player.validationState for player in loaded.players} == {
        "Rennie, Q Sophie": "uncertain",
        "Smith, Ella": "corrected",
    }


def _namedPlayer(name: str, passing: int = 10) -> SquadModelPlayer:
    return SquadModelPlayer(
        name=name,
        positions="M (C)",
        ca="100",
        pa="120",
        confidence=0.9,
        attributes=(("passing", passing),),
    )


def testSupplementarySevenPlayerImportMergesWithoutDeletingOthers() -> None:
    """A filtered 7-row capture updates known players, adds the missing one, and leaves the rest."""

    existing = tuple(_namedPlayer(f"Player {index:02d}", passing=10) for index in range(1, 32))
    incoming = [
        ExtractedPlayer(f"Player {index:02d}", "M (C)", "111", "125", {"passing": 14}, 0.95)
        for index in (1, 2, 3, 4, 5, 6)
    ]
    incoming.append(ExtractedPlayer("Player 32", "ST (C)", "130", "140", {"passing": 16}, 0.96))

    merged = squadPlayersMerge(existing, incoming, sourceImportSessionId=99)

    byName = {player.name: player for player in merged}
    assert len(merged) == 32
    assert byName["Player 32"].ca == "130"
    assert byName["Player 32"].attributes == (("passing", 16),)
    assert byName["Player 01"].ca == "111"
    assert byName["Player 01"].attributes == (("passing", 14),)
    assert byName["Player 31"].ca == "100"
    assert byName["Player 31"].attributes == (("passing", 10),)
    assert byName["Player 07"].ca == "100"


def testModelRefreshFromEvidenceAddsMissingPlayerWithoutReOcr(tmp_path) -> None:
    """Saved import rows must refresh the object model; absence is not deletion."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    first = [
        ExtractedPlayer(f"Player {index:02d}", "M (C)", "100", "120", {"passing": 10}, 0.9)
        for index in range(1, 32)
    ]
    database.squadImportBatchSave(["/captures/full.png"], first, "First Team")
    service = SquadModelService(database.engine)
    generated = service.modelLoad("First Team")
    assert generated is not None
    assert len(generated.players) == 31

    supplementary = [
        ExtractedPlayer(f"Player {index:02d}", "M (C)", "111", "125", {"passing": 14}, 0.95)
        for index in (1, 2, 3, 4, 5, 6)
    ]
    supplementary.append(
        ExtractedPlayer("Player 32", "ST (C)", "130", "140", {"passing": 16}, 0.96)
    )
    database.squadImportBatchSave(["/captures/filtered-seven.png"], supplementary, "First Team")
    refreshed = service.modelRefreshFromEvidence("First Team")

    assert refreshed is not None
    assert len(refreshed.players) == 32
    byName = {player.name: player for player in refreshed.players}
    assert byName["Player 32"].ca == "130"
    assert dict(byName["Player 01"].attributes)["passing"] == 14
    assert dict(byName["Player 31"].attributes)["passing"] == 10
    assert refreshed.regenerationRequired is False


def testManualNameCorrectionSurvivesEvidenceRefresh(tmp_path) -> None:
    """A corrected model name remains authoritative over later noisy OCR rows."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    noisy = ExtractedPlayer("Smith, Qe Ella", "M (C)", "105", "125", {"passing": 14}, 0.82)
    database.squadImportBatchSave(["/captures/first.png"], [noisy], "First Team")
    service = SquadModelService(database.engine)
    generated = service.modelLoad("First Team")
    assert generated is not None
    corrected = replace(
        generated,
        players=(
            replace(
                generated.players[0],
                name="Smith, Ella",
                validationState="corrected",
            ),
        ),
    )
    service.modelSave(corrected)

    database.squadImportBatchSave(["/captures/second.png"], [noisy], "First Team")
    refreshed = service.modelRefreshFromEvidence("First Team")

    assert refreshed is not None
    assert len(refreshed.players) == 1
    assert refreshed.players[0].name == "Smith, Ella"
    assert refreshed.players[0].validationState == "corrected"
