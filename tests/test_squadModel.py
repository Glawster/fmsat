"""Editable squad object-model persistence tests."""

from datetime import datetime

from fmsat.core.squadModel import SquadModel, SquadModelPlayer, SquadModelService
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
