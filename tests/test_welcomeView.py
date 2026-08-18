"""Welcome workspace behaviour tests."""

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QInputDialog,
    QProgressDialog,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QToolButton,
)

from fmsat.app.welcomeView import (
    PositionRoleGroup,
    SummaryCard,
    WelcomeService,
    WelcomeView,
)
from fmsat.app.window import MainWindow
from fmsat.core.builder.tacticBuilder import TacticBuildIssue
from fmsat.core.builder.tacticModelLoader import TacticModelLoadResult
from fmsat.core.parser import RoleProfileEvidence, TacticalPhase, TacticVocabulary
from fmsat.core.roleKnowledge import RoleKnowledgeService


def _mainWindowCreate() -> MainWindow:
    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    return MainWindow(Mock(), database, (), Mock(), Mock(), Mock())


def _labelTexts(view: WelcomeView) -> list[str]:
    return [label.text() for label in view.findChildren(QLabel)]


def _positionExpand(view: WelcomeView, position: str, qtbot) -> PositionRoleGroup:  # type: ignore[no-untyped-def]
    group = next(
        group
        for group in view.rolesWidget.findChildren(PositionRoleGroup)
        if group.property("position") == position
    )
    qtbot.mouseClick(group.summaryButton, Qt.MouseButton.LeftButton)
    return group


def testWelcomeViewEmptyDatabase(qtbot) -> None:  # type: ignore[no-untyped-def]

    window = _mainWindowCreate()
    qtbot.addWidget(window)

    assert window.contentStack.currentWidget() is window.welcomeView
    assert "No tactics have been imported yet." in _labelTexts(window.welcomeView)
    assert "No squads have been imported yet." in _labelTexts(window.welcomeView)
    assert not window.welcomeView.findChildren(QTableWidget)


def testWorkspaceImportButtonsAreEqualProminentActions(qtbot) -> None:  # type: ignore[no-untyped-def]

    window = _mainWindowCreate()
    qtbot.addWidget(window)

    buttons = window.welcomeView.findChildren(
        QToolButton,
        "workspaceActionButton",
    )

    assert [button.text() for button in buttons] == [
        "Import Tactic",
        "Import Squad",
        "Import Role",
    ]
    assert buttons[0].size() == buttons[1].size()
    assert "background-color" in buttons[0].styleSheet()
    assert "border-radius" in buttons[0].styleSheet()


def testMainMenuBarIsAvailableWithFileAndViewMenus(qtbot) -> None:  # type: ignore[no-untyped-def]

    window = _mainWindowCreate()
    qtbot.addWidget(window)

    assert [action.text() for action in window.menuBar().actions()] == ["&File", "&View"]


def testViewMenuIncludesRolesAndShowsWelcomeRolesPanel(qtbot) -> None:  # type: ignore[no-untyped-def]

    window = _mainWindowCreate()
    qtbot.addWidget(window)
    menuActions = window.menuBar().actions()
    viewMenu = menuActions[1].menu()
    window.contentStack.setCurrentWidget(window.reviewWidget)

    assert viewMenu is not None
    assert [action.text() for action in viewMenu.actions()] == [
        "Tactics",
        "Squads",
        "Roles",
        "Players",
        "Settings",
        "",
        "Show Status Log",
        "Show OCR Zones",
    ]

    window.rolesAction.trigger()

    assert window.contentStack.currentWidget() is window.welcomeView


def testConfirmedRoleCaptureRefreshesWelcomePanel(qtbot, monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    roleKnowledge = Mock()
    roleKnowledge.definitionExists.return_value = False
    vocabulary = TacticVocabulary()
    window = MainWindow(
        Mock(),
        database,
        (),
        Mock(),
        Mock(),
        Mock(),
        roleKnowledge,
        vocabulary,
    )
    qtbot.addWidget(window)
    selections = iter((("Channel Forward (CHF)", True),))
    monkeypatch.setattr(QInputDialog, "getItem", lambda *args: next(selections))
    evidence = RoleProfileEvidence(
        position="ST (C)",
        roleName="Channel Forward",
        phase=TacticalPhase.IN_POSSESSION,
        abbreviation="CHF",
        keyAttributes=("finishing",),
    )
    monkeypatch.setattr(
        window,
        "_screenshotAcquire",
        lambda *args: SimpleNamespace(roleProfile=evidence),
    )
    monkeypatch.setattr(window, "_screenshotPersist", lambda *args: tmp_path / "role.png")
    dialog = Mock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    dialog.savedPath = tmp_path / "channelForward.yaml"
    monkeypatch.setattr("fmsat.app.window.RoleProfileReviewDialog", lambda *args, **kwargs: dialog)
    changed = QSignalSpy(window.dataChanged)

    window.roleProfileImport()

    assert changed.count() == 1


def testRoleImportUsesDetectedScreenshotPosition(qtbot, monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    roleKnowledge = Mock()
    roleKnowledge.definitionExists.return_value = False
    vocabulary = TacticVocabulary()
    window = MainWindow(
        Mock(),
        database,
        (),
        Mock(),
        Mock(),
        Mock(),
        roleKnowledge,
        vocabulary,
    )
    qtbot.addWidget(window)
    monkeypatch.setattr(QInputDialog, "getItem", lambda *args: ("Channel Forward (CHF)", True))
    evidence = RoleProfileEvidence(
        position="ST (C)",
        roleName="Channel Forward",
        phase=TacticalPhase.IN_POSSESSION,
        abbreviation="CHF",
        keyAttributes=("finishing",),
    )
    monkeypatch.setattr(
        window,
        "_screenshotAcquire",
        lambda *args: SimpleNamespace(roleProfile=evidence),
    )
    monkeypatch.setattr(window, "_screenshotPersist", lambda *args: tmp_path / "role.png")
    observed = {}

    def dialogCreate(*args, **kwargs):  # type: ignore[no-untyped-def]
        observed["expectedPosition"] = args[1]
        dialog = Mock()
        dialog.exec.return_value = QDialog.DialogCode.Accepted
        dialog.savedPath = tmp_path / "channelForward.yaml"
        return dialog

    monkeypatch.setattr("fmsat.app.window.RoleProfileReviewDialog", dialogCreate)

    window.roleProfileImport()

    assert observed["expectedPosition"] == "STC"


def testRoleSelectionLoadsCapturedDefinitionForEditing(qtbot, monkeypatch) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    roleKnowledge = Mock()
    roleKnowledge.definitionExists.return_value = True
    roleKnowledge.definitionLoad.return_value = {
        "displayName": "Inside Forward",
        "abbreviations": ["IF"],
        "positions": ["AML", "AMR"],
        "behaviours": ["movesInside", "goalThreat"],
        "keyAttributes": ["off_the_ball"],
        "playerInstructions": ["getFurtherForward"],
    }
    window = MainWindow(
        Mock(),
        database,
        (),
        Mock(),
        Mock(),
        Mock(),
        roleKnowledge,
        TacticVocabulary(),
    )
    qtbot.addWidget(window)
    dialog = Mock()
    dialog.exec.return_value = QDialog.DialogCode.Rejected
    dialogCreate = Mock(return_value=dialog)
    monkeypatch.setattr("fmsat.app.window.RoleProfileReviewDialog", dialogCreate)

    window.roleShow("insideForward")

    evidence = dialogCreate.call_args.args[0]
    assert evidence.phase is None
    assert evidence.behaviours == ("movesInside", "goalThreat")
    assert dialogCreate.call_args.kwargs["supportedPositions"] == ("AML", "AMR")
    assert dialogCreate.call_args.kwargs["replaceExisting"] is True


def testWelcomeViewPopulated(qtbot) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = [
        SimpleNamespace(name="High Press", captureCount=3, formationImage=None)
    ]
    database.squadRecords.return_value = [
        SimpleNamespace(name="First Team", captureCount=2, playerCount=24)
    ]
    window = MainWindow(Mock(), database, (), Mock(), Mock(), Mock())
    qtbot.addWidget(window)

    labels = _labelTexts(window.welcomeView)

    assert "Tactics (1)" in labels
    assert "Squads (1)" in labels
    assert "High Press" in labels
    assert "First Team" in labels


def testWelcomeViewShowsOnlyCapturedRolesInTacticalOrder(qtbot) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    captured = {
        "centreForward",
        "attackingMidfielder",
        "boxToBoxMidfielder",
        "defensiveMidfielder",
        "centreBack",
        "sweeperKeeper",
    }
    roleKnowledge = Mock()
    roleKnowledge.definitionExists.side_effect = lambda role: role in captured
    view = WelcomeView(
        WelcomeService(database, TacticVocabulary(), roleKnowledge),
        (),
        Mock(),
        Mock(),
        Mock(),
    )
    qtbot.addWidget(view)

    labels = [label.text() for label in view.rolesWidget.findChildren(QLabel)]
    groups = view.rolesWidget.findChildren(PositionRoleGroup)
    groupPositions = [group.property("position") for group in groups]

    assert "Roles (6)" in labels
    assert groupPositions == sorted(groupPositions, key=WelcomeService.positionSortKey)
    assert {"STC", "AMC", "MC", "DM", "DC", "GK"}.issubset(groupPositions)
    assert all(not group.rolesContainer.isVisible() for group in groups)
    assert "Ball-Playing Goalkeeper" not in labels


def testPositionSummaryExpandsItsCapturedRoles(qtbot) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    roleKnowledge = Mock()
    roleKnowledge.definitionExists.side_effect = lambda role: role == "insideForward"
    roleKnowledge.definitionLoad.return_value = {"behaviours": ["movesInside"]}
    view = WelcomeView(
        WelcomeService(database, TacticVocabulary(), roleKnowledge),
        (),
        Mock(),
        Mock(),
        Mock(),
    )
    qtbot.addWidget(view)
    view.show()

    group = next(
        group
        for group in view.rolesWidget.findChildren(PositionRoleGroup)
        if group.property("position") == "AML"
    )

    assert group.summaryButton.text() == "AM (L) — 1 role"
    assert not group.rolesContainer.isVisible()

    qtbot.mouseClick(group.summaryButton, Qt.MouseButton.LeftButton)

    assert group.rolesContainer.isVisible()
    assert group.summaryButton.arrowType() == Qt.ArrowType.NoArrow
    assert any(
        card.property("summaryName") == "Inside Forward"
        for card in group.findChildren(SummaryCard)
    )

    qtbot.mouseClick(group.summaryButton, Qt.MouseButton.LeftButton)

    assert not group.rolesContainer.isVisible()
    assert group.summaryButton.arrowType() == Qt.ArrowType.NoArrow


def testCapturedRoleCardShowsBehavioursAndOpensEditor(qtbot) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    roleKnowledge = Mock()
    roleKnowledge.definitionExists.side_effect = lambda role: role == "insideForward"
    roleKnowledge.definitionLoad.return_value = {"behaviours": ["movesInside", "goalThreat"]}
    roleOpen = Mock()
    view = WelcomeView(
        WelcomeService(database, TacticVocabulary(), roleKnowledge),
        (),
        Mock(),
        Mock(),
        Mock(),
        roleOpen,
    )
    qtbot.addWidget(view)
    view.show()
    _positionExpand(view, "AML", qtbot)
    card = next(
        card
        for card in view.findChildren(SummaryCard)
        if card.property("summaryName") == "Inside Forward"
    )

    assert any("Behaviours: Moves Inside, Goal Threat" in text for text in _labelTexts(view))
    assert not card.findChildren(QPushButton)

    qtbot.mouseClick(card, Qt.MouseButton.LeftButton)

    roleOpen.assert_called_once_with("insideForward")


def testWelcomeViewShowsUserDefinedRolesFromConfirmedYaml(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    service = RoleKnowledgeService(tmp_path, TacticVocabulary(), {"marking"})
    evidence = RoleProfileEvidence(
        position="DM",
        roleName="Dropping Defensive Midfielder",
        phase=TacticalPhase.OUT_OF_POSSESSION,
        abbreviation="DDM",
        behaviours=("movesBackToCB",),
        keyAttributes=("marking",),
    )
    draft = service.evidenceVerify(
        evidence,
        "DM",
        "defensiveMidfielder",
        adoptDetectedRole=True,
        supportedPositions=("DM",),
    )
    service.definitionConfirm(draft)
    confirmedRole = service.definitionsList()[0]
    roleOpen = Mock()
    view = WelcomeView(
        WelcomeService(database, TacticVocabulary(), service),
        (),
        Mock(),
        Mock(),
        Mock(),
        roleOpen,
    )
    qtbot.addWidget(view)
    view.show()
    _positionExpand(view, "DM", qtbot)

    labels = _labelTexts(view)
    card = next(
        card
        for card in view.findChildren(SummaryCard)
        if card.property("summaryName") == "Dropping Defensive Midfielder"
    )

    assert "Roles (1)" in labels
    assert "Dropping Defensive Midfielder" in labels
    assert any("Behaviours: Moves Back To" in text for text in labels)

    qtbot.mouseClick(card, Qt.MouseButton.LeftButton)

    roleOpen.assert_called_once_with(confirmedRole.roleCode)


def testTacticAndSquadCardsOpenWhenSelected(qtbot) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = [
        SimpleNamespace(name="Press", captureCount=1, formationImage=None)
    ]
    database.squadRecords.return_value = [
        SimpleNamespace(name="First Team", captureCount=1, playerCount=20)
    ]
    tacticOpen = Mock()
    squadOpen = Mock()
    view = WelcomeView(WelcomeService(database), (), tacticOpen, Mock(), squadOpen)
    qtbot.addWidget(view)
    cards = {card.property("summaryName"): card for card in view.findChildren(SummaryCard)}

    qtbot.mouseClick(cards["Press"], Qt.MouseButton.LeftButton)
    qtbot.mouseClick(cards["First Team"], Qt.MouseButton.LeftButton)

    tacticOpen.assert_called_once_with("Press")
    squadOpen.assert_called_once_with("First Team")
    assert not cards["Press"].findChildren(QPushButton)
    assert not cards["First Team"].findChildren(QPushButton)


def testTacticCardShowsProcessButtonWhenNoExtractedData(qtbot) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = [
        SimpleNamespace(
            name="Press",
            captureCount=3,
            formationImage=None,
            hasStructuredData=False,
            hasObjectModelData=False,
        )
    ]
    database.squadRecords.return_value = []
    tacticOpen = Mock()
    tacticProcess = Mock()
    view = WelcomeView(WelcomeService(database), (), tacticOpen, tacticProcess, Mock())
    qtbot.addWidget(view)

    card = next(
        card
        for card in view.findChildren(SummaryCard)
        if card.property("summaryName") == "Press"
    )
    processButton = next(
        button for button in card.findChildren(QToolButton) if button.text() == "Process"
    )

    qtbot.mouseClick(processButton, Qt.MouseButton.LeftButton)

    tacticProcess.assert_called_once_with("Press")


def testTacticCardHidesProcessButtonWhenModelExists(qtbot) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = [
        SimpleNamespace(
            name="Press",
            captureCount=3,
            formationImage=None,
            hasStructuredData=False,
            hasObjectModelData=True,
        )
    ]
    database.squadRecords.return_value = []
    tacticOpen = Mock()
    tacticProcess = Mock()
    view = WelcomeView(WelcomeService(database), (), tacticOpen, tacticProcess, Mock())
    qtbot.addWidget(view)

    card = next(
        card
        for card in view.findChildren(SummaryCard)
        if card.property("summaryName") == "Press"
    )
    processButtons = [
        button for button in card.findChildren(QToolButton) if button.text() == "Process"
    ]

    assert not processButtons


def testWelcomeViewRefreshesFromService(qtbot) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.side_effect = [
        [],
        [SimpleNamespace(name="Press", captureCount=1, formationImage=None)],
    ]
    database.squadRecords.return_value = []
    view = WelcomeView(WelcomeService(database), (), Mock(), Mock(), Mock())
    qtbot.addWidget(view)

    view.refresh()

    assert "Press" in _labelTexts(view)


def testExpectedRoleChoicesHideStateAndOrderMissingBeforeKnown(
    qtbot, monkeypatch
) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    roleKnowledge = Mock()
    roleKnowledge.definitionExists.side_effect = lambda role: role == "advancedPlaymaker"
    vocabulary = TacticVocabulary()
    window = MainWindow(
        Mock(),
        database,
        (),
        Mock(),
        Mock(),
        Mock(),
        roleKnowledge,
        vocabulary,
    )
    qtbot.addWidget(window)
    choices = []

    def selectionCapture(*args):  # type: ignore[no-untyped-def]
        choices.extend(args[3])
        return "", False

    monkeypatch.setattr(QInputDialog, "getItem", selectionCapture)

    window.roleProfileImport()

    assert choices[0] == "New role…"
    assert choices[-1] == "Advanced Playmaker (AP)"
    assert not any("Missing" in choice or "Known" in choice for choice in choices)


def testNewRoleChoiceUsesPositionDetectedFromScreenshot(
    qtbot, monkeypatch, tmp_path
) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    vocabulary = TacticVocabulary()
    window = MainWindow(
        Mock(),
        database,
        (),
        Mock(),
        Mock(),
        Mock(),
        Mock(definitionExists=Mock(return_value=False)),
        vocabulary,
    )
    qtbot.addWidget(window)
    selection = Mock(return_value=("New role…", True))
    monkeypatch.setattr(QInputDialog, "getItem", selection)
    evidence = RoleProfileEvidence(
        position="AM (C)",
        roleName="New Role",
        phase=TacticalPhase.IN_POSSESSION,
        abbreviation="NR",
    )
    monkeypatch.setattr(
        window,
        "_screenshotAcquire",
        lambda *args: SimpleNamespace(roleProfile=evidence),
    )
    monkeypatch.setattr(window, "_screenshotPersist", lambda *args: tmp_path / "role.png")
    observed = {}

    def dialogCreate(*args, **kwargs):  # type: ignore[no-untyped-def]
        observed["expectedPosition"] = args[1]
        dialog = Mock()
        dialog.exec.return_value = QDialog.DialogCode.Accepted
        dialog.savedPath = tmp_path / "newRole.yaml"
        return dialog

    monkeypatch.setattr("fmsat.app.window.RoleProfileReviewDialog", dialogCreate)

    window.roleProfileImport()

    assert selection.call_count == 1
    assert observed["expectedPosition"] == "AMC"


def testTacticShowOpensIncompleteViewWhenNoModelData(qtbot) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    database.tacticDetailRecord.return_value = None
    window = MainWindow(Mock(), database, (), Mock(), Mock(), Mock())
    qtbot.addWidget(window)
    window.tacticModelLoader.tacticLoad = Mock(
        return_value=TacticModelLoadResult(
            tactic=None,
            source="none",
            issues=(
                TacticBuildIssue(
                    "missingStructuredDefinition",
                    "No screenshot-derived tactic definition exists",
                ),
            ),
            complete=False,
            confirmed=False,
        )
    )

    window.tacticShow("Unavailable Tactic")

    assert window.contentStack.currentWidget() is window.tacticDetailView
    assert window.tacticDetailView.titleLabel.text() == "Unavailable Tactic"
    labels = [label.text() for label in window.tacticDetailView.findChildren(QLabel)]
    assert "Tactic Workspace  ·  Incomplete Data" in labels
    assert "Incomplete data" in labels


def testTacticModelImportUsesProcessingFlow(qtbot) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    database.tacticDetailRecord.return_value = None
    window = MainWindow(Mock(), database, (), Mock(), Mock(), Mock())
    qtbot.addWidget(window)
    window.tacticProcess = Mock()
    window._tacticImportRun = Mock()

    window.tacticModelImport("High Press")

    window.tacticProcess.assert_called_once_with("High Press", forceRebuild=True)
    window._tacticImportRun.assert_not_called()


def testIncompleteRegenerationRetainsExistingObjectModel(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Incomplete screenshot evidence must not reach the object-model store."""

    window = _mainWindowCreate()
    qtbot.addWidget(window)
    window.tacticModelLoader.tacticLoad = Mock(
        return_value=SimpleNamespace(source="objectModel")
    )
    window.tacticScreenshotExtractor.tacticExtract = Mock(
        return_value=SimpleNamespace(
            structuredCreated=True,
            complete=False,
            message="Observed tactic data extracted with unresolved coverage",
        )
    )
    changed = QSignalSpy(window.dataChanged)

    window.tacticProcess("High Press", openDetail=False, forceRebuild=True)

    assert window.tacticModelLoader.tacticLoad.call_args_list == [
        (("High Press",), {}),
        (("High Press",), {"preferStructured": True}),
    ]
    assert changed.count() == 0
    assert "existing model retained" in window.statusBar().currentMessage()
    assert window.tacticProcessStatuses["high press"] == "Regeneration failed"


def testStatusLogShowsHistoricalMessagesMostRecentFirst(qtbot) -> None:  # type: ignore[no-untyped-def]
    window = _mainWindowCreate()
    qtbot.addWidget(window)

    window.statusBar().showMessage("First operation", 10000)
    window.statusBar().showMessage("Latest operation", 10000)
    window.statusLogShow()

    assert window.statusLogDialog is not None
    qtbot.addWidget(window.statusLogDialog)
    content = window.statusLogDialog.findChild(QPlainTextEdit, "statusLogContent")
    assert content is not None
    lines = content.toPlainText().splitlines()
    assert "Latest operation" in lines[0]
    assert "First operation" in lines[1]


def testTacticProgressDialogRemainsReadable(qtbot) -> None:  # type: ignore[no-untyped-def]
    window = _mainWindowCreate()
    qtbot.addWidget(window)
    progress = window._tacticProgressCreate()
    qtbot.addWidget(progress)

    MainWindow._progressUpdate(progress, "Reading screenshot evidence...", 2)

    assert progress.width() >= 560
    assert progress.height() >= 140
    assert progress.labelText() == "Reading screenshot evidence..."
    assert progress.value() == 2
    assert progress.objectName() == "tacticProgressDialog"
    assert "background-color: #101f2e" in progress.styleSheet()
    assert "QProgressBar::chunk" in progress.styleSheet()


def testBackgroundRunKeepsQtEventLoopResponsive(qtbot) -> None:  # type: ignore[no-untyped-def]
    window = _mainWindowCreate()
    qtbot.addWidget(window)
    eventObserved = []
    QTimer.singleShot(10, lambda: eventObserved.append(True))

    result = window._backgroundRun(lambda: "finished")

    assert result == "finished"
    assert eventObserved == [True]


def testTacticProgressUsesBusyStateDuringOcr(qtbot) -> None:  # type: ignore[no-untyped-def]
    window = _mainWindowCreate()
    qtbot.addWidget(window)
    progress = window._tacticProgressCreate()
    qtbot.addWidget(progress)

    MainWindow._progressBusy(progress, "Reading screenshot evidence with OCR...")

    assert progress.minimum() == 0
    assert progress.maximum() == 0
    assert progress.labelText() == "Reading screenshot evidence with OCR..."

    MainWindow._progressRestore(progress, "Screenshot extraction finished.", 3)

    assert progress.minimum() == 0
    assert progress.maximum() == 6
    assert progress.value() == 3


def testTacticProcessRejectsUnavailableScreenshotEvidence(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Missing capture files must not recreate the removed template fallback model."""

    from fmsat.core.detection import ScreenType
    from fmsat.database import Database, ObjectModelTactic
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    for screenType in (
        ScreenType.TACTIC_FORMATION,
        ScreenType.TACTIC_IN_POSSESSION,
        ScreenType.TACTIC_OUT_OF_POSSESSION,
    ):
        database.tacticImportSave(f"/captures/{screenType.value}.png", screenType, "High Press")

    window = MainWindow(Mock(), database, (), Mock(), Mock(), Mock())
    qtbot.addWidget(window)

    window.tacticProcess("High Press", openDetail=False)

    with Session(database.engine) as session:
        stored = session.scalar(
            select(ObjectModelTactic).where(ObjectModelTactic.normalizedName == "high press")
        )
        assert stored is None

    assert "no model was saved" in window.statusBar().currentMessage().casefold()
