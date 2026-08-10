"""Welcome workspace behaviour tests."""

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QInputDialog,
    QPushButton,
    QTableWidget,
    QToolButton,
)

from fmsat.app.welcomeView import SummaryCard, WelcomeService, WelcomeView
from fmsat.app.window import MainWindow
from fmsat.core.parser import RoleProfileEvidence, TacticalPhase, TacticVocabulary
from fmsat.core.roleKnowledge import RoleKnowledgeService


def _mainWindowCreate() -> MainWindow:
    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    return MainWindow(Mock(), database, (), Mock(), Mock(), Mock())


def _labelTexts(view: WelcomeView) -> list[str]:
    return [label.text() for label in view.findChildren(QLabel)]


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
    )
    qtbot.addWidget(view)

    labels = [label.text() for label in view.rolesWidget.findChildren(QLabel)]
    roleNames = [
        text
        for text in labels
        if text
        in {
            "Centre Forward",
            "Attacking Midfielder",
            "Box-to-Box Midfielder",
            "Defensive Midfielder",
            "Centre-Back",
            "Sweeper Keeper",
        }
    ]

    assert "Roles (6)" in labels
    assert roleNames == [
        "Centre Forward",
        "Attacking Midfielder",
        "Box-to-Box Midfielder",
        "Defensive Midfielder",
        "Centre-Back",
        "Sweeper Keeper",
    ]
    assert "Ball-Playing Goalkeeper" not in labels


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
        roleOpen,
    )
    qtbot.addWidget(view)
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
    roleOpen = Mock()
    view = WelcomeView(
        WelcomeService(database, TacticVocabulary(), service),
        (),
        Mock(),
        Mock(),
        roleOpen,
    )
    qtbot.addWidget(view)

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

    roleOpen.assert_called_once_with(f"roleID:{draft.roleID}")


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
    view = WelcomeView(WelcomeService(database), (), tacticOpen, squadOpen)
    qtbot.addWidget(view)
    cards = {card.property("summaryName"): card for card in view.findChildren(SummaryCard)}

    qtbot.mouseClick(cards["Press"], Qt.MouseButton.LeftButton)
    qtbot.mouseClick(cards["First Team"], Qt.MouseButton.LeftButton)

    tacticOpen.assert_called_once_with("Press")
    squadOpen.assert_called_once_with("First Team")
    assert not cards["Press"].findChildren(QPushButton)
    assert not cards["First Team"].findChildren(QPushButton)


def testWelcomeViewRefreshesFromService(qtbot) -> None:  # type: ignore[no-untyped-def]

    database = Mock()
    database.tacticRecords.side_effect = [
        [],
        [SimpleNamespace(name="Press", captureCount=1, formationImage=None)],
    ]
    database.squadRecords.return_value = []
    view = WelcomeView(WelcomeService(database), (), Mock(), Mock())
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


def testNewRoleChoiceOffersPositionsInTacticalOrder(qtbot, monkeypatch) -> None:  # type: ignore[no-untyped-def]

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
    positionChoices = []
    calls = 0

    def selectionChooseNew(*args):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        if calls == 1:
            return "New role…", True
        positionChoices.extend(args[3])
        return "", False

    monkeypatch.setattr(QInputDialog, "getItem", selectionChooseNew)

    window.roleProfileImport()

    ranks = [WelcomeService.positionSortKey(position)[0] for position in positionChoices]
    assert ranks == sorted(ranks)
    assert ranks[0] == 0
    assert ranks[-1] == 5
