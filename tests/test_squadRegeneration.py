"""Squad regeneration UI and service routing tests."""

from datetime import datetime
from types import SimpleNamespace
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
    assert view.regenerationProgress is not None
    assert view.regenerationProgress.objectName() == "squadRegenerationProgressDialog"
    assert view.regenerationProgress.minimum() == 0
    assert view.regenerationProgress.maximum() == 0


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


def testRegenerationMergesComplementaryAttributeViewsUsingNewestValues() -> None:
    """A GK attribute capture should add attributes without discarding older squad evidence."""

    newest = SimpleNamespace(
        name="Ada Keeper",
        positions="GK",
        ca="110",
        pa="125",
        confidence=0.98,
        importSessionId=12,
        attributes=[
            SimpleNamespace(attributeName="reflexes", attributeValue=16),
            SimpleNamespace(attributeName="handling", attributeValue=None),
            SimpleNamespace(attributeName="throwing", attributeValue=15),
        ],
    )
    older = SimpleNamespace(
        name="Ada Keeper",
        positions="GK",
        ca="108",
        pa="125",
        confidence=0.95,
        importSessionId=8,
        attributes=[
            SimpleNamespace(attributeName="reflexes", attributeValue=14),
            SimpleNamespace(attributeName="handling", attributeValue=13),
            SimpleNamespace(attributeName="concentration", attributeValue=12),
        ],
    )

    player = SquadModelService._playerFromEvidenceRows((newest, older))
    attributes = {
        attribute.attributeName: attribute.attributeValue
        for attribute in player.attributes
    }

    assert player.ca == "110"
    assert player.sourceImportSessionId == 12
    assert attributes == {
        "concentration": 12,
        "handling": 13,
        "reflexes": 16,
        "throwing": 15,
    }
