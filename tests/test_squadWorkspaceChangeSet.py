"""Regression coverage for the squad-workspace presentation change set."""

from datetime import datetime
from importlib.resources import files
from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from fmsat.app.squadDetailModel import SquadDetailModel
from fmsat.app.squadDetailView import SquadDetailView
from fmsat.core.squadModel import SquadModel


def _detail() -> SquadDetailModel:
    squad = SquadModel(
        name="First Team",
        players=(),
        generatedAt=datetime(2026, 8, 17),
        updatedAt=datetime(2026, 8, 17),
        evidenceSuperseded=False,
        regenerationRequired=False,
    )
    return SquadDetailModel(
        squad=squad,
        tacticName="Libero Whealdstone",
        availableTactics=("Libero Whealdstone",),
        sourceStatus="Generated from screenshot evidence",
        updated="17 Aug 2026 09:00",
        requiredPositionCount=0,
        roles=(),
    )


def testFactCardsHaveVisibleHeaderStyle(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Dark summary cards must explicitly style their header labels."""

    view = SquadDetailView()
    qtbot.addWidget(view)
    view.squadShow("Wealdstone", _detail())

    labels = {
        label.text()
        for label in view.findChildren(QLabel)
        if label.objectName() == "factLabel"
    }
    stylesheet = files("fmsat.app").joinpath("fmsat.qss").read_text(encoding="utf-8")

    assert labels == {
        "PLAYERS",
        "TACTIC",
        "UNIQUE TACTIC ROLES",
        "COVERED UNIQUE ROLES",
        "STATUS",
    }
    assert "QLabel#factLabel" in stylesheet


def testRegenerateButtonForcesCurrentModelThroughRegenerationPath(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Regenerate must do real work even when the current model is not marked stale."""

    host = QWidget()
    qtbot.addWidget(host)
    host.squadModelService = SimpleNamespace(modelSave=Mock())  # type: ignore[attr-defined]
    host.dataChanged = SimpleNamespace(emit=Mock())  # type: ignore[attr-defined]
    host.squadShow = Mock()  # type: ignore[attr-defined]

    view = SquadDetailView(host)
    view.squadShow("Wealdstone", _detail())
    qtbot.mouseClick(view.regenerateButton, Qt.MouseButton.LeftButton)

    host.squadModelService.modelSave.assert_called_once()  # type: ignore[attr-defined]
    regenerationModel = host.squadModelService.modelSave.call_args.args[0]  # type: ignore[attr-defined]
    assert regenerationModel.regenerationRequired is True
    host.dataChanged.emit.assert_called_once()  # type: ignore[attr-defined]
    host.squadShow.assert_called_once_with("Wealdstone", "Libero Whealdstone")  # type: ignore[attr-defined]
