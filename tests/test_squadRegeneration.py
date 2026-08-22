"""Squad regeneration UI and service routing tests."""

from datetime import datetime
import logging
from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow

from fmsat.app.squadDetailModel import SquadDetailModel
from fmsat.app.squadDetailView import (
    SquadDetailView,
    _SquadRegenerationProgressHandler,
)
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


def _detail(squad: SquadModel) -> SquadDetailModel:
    return SquadDetailModel(
        squad=squad,
        tacticName="High Press",
        availableTactics=("High Press",),
        sourceStatus=(
            "Regeneration required — newer squad screenshots exist"
            if squad.regenerationRequired
            else "Generated from screenshot evidence"
        ),
        updated="15 Aug 2026 22:00",
        requiredPositionCount=0,
        roles=(),
    )


def testRegenerationButtonAppearsForStaleSquadAndRequestsRegeneration(qtbot) -> None:  # type: ignore[no-untyped-def]
    """A stale squad should expose an explicit rebuild action using saved evidence."""

    squad = _model(regenerationRequired=True)
    view = SquadDetailView()
    qtbot.addWidget(view)
    requested: list[str] = []
    view.modelRegenerateRequested.connect(requested.append)

    view.squadShow("First Team", _detail(squad))

    assert view.regenerateButton.text() == "Regenerate Squad Model"
    qtbot.mouseClick(view.regenerateButton, Qt.MouseButton.LeftButton)
    assert requested == ["First Team"]
    assert view.regenerationProgress is not None
    assert view.regenerationProgress.objectName() == "squadRegenerationProgressDialog"
    assert view.regenerationProgress.minimum() == 0
    assert view.regenerationProgress.maximum() == 0


def testRegenerationButtonAppearsForCurrentSquad(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Current evidence may be explicitly re-read after parser/configuration improvements."""

    squad = _model(regenerationRequired=False)
    view = SquadDetailView()
    qtbot.addWidget(view)
    requested: list[str] = []
    view.modelRegenerateRequested.connect(requested.append)

    view.squadShow("First Team", _detail(squad))

    assert view.regenerateButton.text() == "Regenerate Squad Model"
    qtbot.mouseClick(view.regenerateButton, Qt.MouseButton.LeftButton)
    assert requested == ["First Team"]


def testReassessRefreshesAnalysisWithoutRegeneratingEvidence(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Reassessment reloads current policy and evidence without model regeneration."""

    window = QMainWindow()
    qtbot.addWidget(window)
    window.squadModelService = Mock()
    window.squadShow = Mock()
    view = SquadDetailView(window)
    window.setCentralWidget(view)
    requested: list[str] = []
    view.modelReassessRequested.connect(requested.append)
    view.squadShow("First Team", _detail(_model(regenerationRequired=False)))

    qtbot.mouseClick(view.reassessButton, Qt.MouseButton.LeftButton)

    assert requested == ["First Team"]
    window.squadShow.assert_called_once_with("First Team", "High Press")
    window.squadModelService.modelSave.assert_not_called()


def testRegenerationProgressUsesExistingOcrMilestones() -> None:
    """The UI should reuse the production OCR x/y log milestones as determinate progress."""

    progress: list[tuple[int, int, str]] = []
    handler = _SquadRegenerationProgressHandler(
        lambda current, total, message: progress.append((current, total, message))
    )
    handler.emit(
        logging.LogRecord(
            "fmsat",
            logging.INFO,
            __file__,
            1,
            "...squad regeneration OCR 3/8: screenshot.png",
            (),
            None,
        )
    )

    assert progress == [(3, 8, "Reading squad screenshot 3 of 8…")]


def testRegenerationProgressReservesFinalStageForRoleAssessment(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Screenshot OCR progress should leave one final step for reassessment/refresh."""

    view = SquadDetailView()
    qtbot.addWidget(view)
    view.regenerationProgress = view._regenerationProgressCreate()

    view._regenerationProgressUpdate(4, 8, "Reading squad screenshot 4 of 8…")

    assert view.regenerationProgress.minimum() == 0
    assert view.regenerationProgress.maximum() == 9
    assert view.regenerationProgress.value() == 3
    assert view.regenerationProgress.labelText() == "Reading squad screenshot 4 of 8…"
    assert view.regenerationProgressTotal == 8


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
        attribute.attributeName: attribute.attributeValue for attribute in player.attributes
    }

    assert player.ca == "110"
    assert player.sourceImportSessionId == 12
    assert attributes == {
        "concentration": 12,
        "handling": 13,
        "reflexes": 16,
        "throwing": 15,
    }
