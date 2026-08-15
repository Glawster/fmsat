"""Squad regeneration UI and service routing tests."""

from datetime import datetime
from unittest.mock import Mock

from PySide6.QtCore import Qt

from fmsat.app.squadDetailModel import SquadDetailModel
from fmsat.app.squadDetailView import SquadDetailView
from fmsat.core.squadModel import SquadModel, SquadModelService


def _model(*, regenerationRequired: bool) -> SquadModel:
    return SquadModel(
        name="First Team",
        players=(),
        generatedAt=datetime(2026, 8, 15),
        updatedAt=datetime(2026, 8, 15),
        evidenceSuperseded=False,
        regenerationRequired=regenerationRequired,
    )


def testRegenerationButtonAppearsForStaleSquadAndRequestsOriginalModel(qtbot) -> None:  # type: ignore[no-untyped-def]
    """A stale squad should expose an explicit rebuild action using saved evidence."""

    squad = _model(regenerationRequired=True)
    detail = SquadDetailModel(
        squad=squad,
        tacticName="High Press",
        availableTactics=("High Press",),
        sourceStatus="Regeneration required — newer squad screenshots exist",
        updated="15 Aug 2026 22:00",
        requiredPositionCount=0,
        roles=(),
    )
    view = SquadDetailView()
    qtbot.addWidget(view)
    requested = []
    view.modelSaveRequested.connect(requested.append)

    view.squadShow("First Team", detail)

    assert view.regenerateButton is not None
    assert view.regenerateButton.text() == "Regenerate Squad Model"
    qtbot.mouseClick(view.regenerateButton, Qt.MouseButton.LeftButton)
    assert requested == [squad]


def testRegenerationButtonIsHiddenForCurrentSquad(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Current screenshot evidence should not offer a redundant regeneration action."""

    squad = _model(regenerationRequired=False)
    detail = SquadDetailModel(
        squad=squad,
        tacticName="High Press",
        availableTactics=("High Press",),
        sourceStatus="Generated from screenshot evidence",
        updated="15 Aug 2026 22:00",
        requiredPositionCount=0,
        roles=(),
    )
    view = SquadDetailView()
    qtbot.addWidget(view)

    view.squadShow("First Team", detail)

    assert view.regenerateButton is None


def testModelSaveRoutesStaleModelToRegeneration() -> None:
    """The existing save signal path should regenerate instead of superseding new evidence."""

    stale = _model(regenerationRequired=True)
    refreshed = _model(regenerationRequired=False)
    service = SquadModelService(Mock())
    service._modelRegenerate = Mock(return_value=refreshed)  # type: ignore[method-assign]

    result = service.modelSave(stale)

    assert result is refreshed
    service._modelRegenerate.assert_called_once_with("First Team")
