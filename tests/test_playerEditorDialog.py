"""Regression coverage for focused squad player editing."""

from datetime import datetime

from PySide6.QtWidgets import QAbstractItemView

from fmsat.app.playerEditorDialog import PlayerEditorDialog
from fmsat.app.squadPlayersWorkspace import SquadPlayersTab
from fmsat.core.config import AttributeDefinition
from fmsat.core.squadModel import SquadModel, SquadModelPlayer


def _player() -> SquadModelPlayer:
    return SquadModelPlayer(
        name="Alessia Russo",
        positions="ST (C)",
        ca="184",
        pa="189",
        confidence=0.98,
        sourceImportSessionId=12,
        validationState="extracted",
        attributes=(("acceleration", 14), ("natural_fitness", None)),
        traits=("Moves Into Channels",),
    )


def _attributes() -> tuple[AttributeDefinition, ...]:
    return (
        AttributeDefinition("acceleration", "Acc", 1),
        AttributeDefinition("natural_fitness", "Nat", 2),
    )


def testPlayerEditorReturnsCorrectedFactsWithoutDerivedScores(qtbot) -> None:  # type: ignore[no-untyped-def]
    dialog = PlayerEditorDialog(_player(), _attributes())
    qtbot.addWidget(dialog)

    dialog.nameInput.setText("Russo, Alessia")
    dialog.attributeInputs["natural_fitness"].setValue(16)
    dialog.selectedTraits = ("Moves Into Channels", "Places Shots")

    edited = dialog.editedPlayer()

    assert edited.name == "Alessia Russo"
    assert dict(edited.attributes)["natural_fitness"] == 16
    assert edited.traits == ("Moves Into Channels", "Places Shots")
    assert edited.sourceImportSessionId == 12
    assert edited.validationState == "corrected"


def testPlayersTabIsBrowseOnlyAndBuildsEditorChanges(qtbot) -> None:  # type: ignore[no-untyped-def]
    model = SquadModel(
        name="First Team",
        players=(_player(),),
        generatedAt=datetime(2026, 8, 18),
        updatedAt=datetime(2026, 8, 18),
        evidenceSuperseded=False,
    )
    tab = SquadPlayersTab(model, _attributes())
    qtbot.addWidget(tab)

    assert tab.table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    assert tab.table.item(0, 0).text() == "Russo, Alessia"

    edited = _player()
    edited = SquadModelPlayer(
        name=edited.name,
        positions=edited.positions,
        ca=edited.ca,
        pa=edited.pa,
        confidence=edited.confidence,
        sourceImportSessionId=edited.sourceImportSessionId,
        validationState="corrected",
        attributes=(("acceleration", 15), ("natural_fitness", 16)),
        traits=("Places Shots",),
    )
    tab._playerRowApply(0, edited)

    rebuilt = tab.modelBuild()
    assert dict(rebuilt.players[0].attributes)["acceleration"] == 15
    assert dict(rebuilt.players[0].attributes)["natural_fitness"] == 16
    assert rebuilt.players[0].traits == ("Places Shots",)
