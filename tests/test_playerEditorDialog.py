"""Regression coverage for focused squad player editing."""

from datetime import datetime
from unittest.mock import patch

from PySide6.QtWidgets import QAbstractItemView, QDialog, QDialogButtonBox, QLabel

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
        attributes=(
            ("acceleration", 14),
            ("natural_fitness", None),
            ("handling", 7),
        ),
        traits=("Moves Into Channels",),
    )


def _attributes() -> tuple[AttributeDefinition, ...]:
    return (
        AttributeDefinition("acceleration", "Acc", 1),
        AttributeDefinition("natural_fitness", "Nat", 2),
        AttributeDefinition("handling", "Han", 3),
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
    # Hidden goalkeeper-only evidence is preserved for an outfield player.
    assert dict(edited.attributes)["handling"] == 7
    assert edited.traits == ("Moves Into Channels", "Places Shots")
    assert edited.sourceImportSessionId == 12
    assert edited.validationState == "corrected"


def testPlayerEditorUsesFullAttributeNamesAndHidesGoalkeeperOnlyFields(qtbot) -> None:  # type: ignore[no-untyped-def]
    dialog = PlayerEditorDialog(_player(), _attributes())
    qtbot.addWidget(dialog)

    labels = {
        label.text()
        for label in dialog.findChildren(QLabel, "playerAttributeLabel")
    }
    assert "Acceleration" in labels
    assert "Natural Fitness" in labels
    assert "Acc" not in labels
    assert "Nat" not in labels
    assert "Handling" not in labels
    assert "handling" not in dialog.attributeInputs


def testGoalkeeperEditorShowsGoalkeeperAttributes(qtbot) -> None:  # type: ignore[no-untyped-def]
    goalkeeper = SquadModelPlayer(
        name="Example Keeper",
        positions="GK",
        ca="120",
        pa="130",
        confidence=0.9,
        attributes=(("acceleration", 10), ("handling", 15)),
    )
    dialog = PlayerEditorDialog(goalkeeper, _attributes())
    qtbot.addWidget(dialog)

    labels = {
        label.text()
        for label in dialog.findChildren(QLabel, "playerAttributeLabel")
    }
    assert "Handling" in labels
    assert "handling" in dialog.attributeInputs


def testPlayerEditorExposesSharedStylingHooks(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The focused editor should retain stable object names used by the shared QSS."""

    dialog = PlayerEditorDialog(_player(), _attributes())
    qtbot.addWidget(dialog)

    assert dialog.objectName() == "playerEditorDialog"
    assert all(
        editor.objectName() == "playerAttributeInput"
        for editor in dialog.attributeInputs.values()
    )
    buttons = dialog.findChild(QDialogButtonBox, "playerEditorButtons")
    assert buttons is not None
    assert buttons.button(QDialogButtonBox.StandardButton.Save).objectName() == "primaryButton"
    assert buttons.button(QDialogButtonBox.StandardButton.Cancel).objectName() == "secondaryButton"


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
        attributes=(
            ("acceleration", 15),
            ("natural_fitness", 16),
            ("handling", 7),
        ),
        traits=("Places Shots",),
    )
    tab._playerRowApply(0, edited)

    rebuilt = tab.modelBuild()
    assert dict(rebuilt.players[0].attributes)["acceleration"] == 15
    assert dict(rebuilt.players[0].attributes)["natural_fitness"] == 16
    assert rebuilt.players[0].traits == ("Places Shots",)


def testPlayersTabLaunchesEditorWithConfiguredAttributes(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The double-click path must retain and pass the configured attribute definitions."""

    attributes = _attributes()
    model = SquadModel(
        name="First Team",
        players=(_player(),),
        generatedAt=datetime(2026, 8, 18),
        updatedAt=datetime(2026, 8, 18),
        evidenceSuperseded=False,
    )
    tab = SquadPlayersTab(model, attributes)
    qtbot.addWidget(tab)

    with patch("fmsat.app.squadPlayersWorkspace.PlayerEditorDialog") as dialogClass:
        dialogClass.return_value.exec.return_value = QDialog.DialogCode.Rejected

        tab._playerEditorOpen(0, 0)

    launchedPlayer, launchedAttributes, launchedParent = dialogClass.call_args.args
    assert launchedPlayer.name == "Alessia Russo"
    assert launchedAttributes == attributes
    assert launchedParent is tab
