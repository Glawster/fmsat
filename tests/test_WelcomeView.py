"""Welcome workspace behaviour tests."""

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtWidgets import QLabel, QInputDialog, QTableWidget, QToolButton

from fmsat.app.welcomeView import WelcomeService, WelcomeView
from fmsat.app.window import MainWindow
from fmsat.core.parser import TacticVocabulary


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
        "Import Role Profile",
    ]
    assert buttons[0].size() == buttons[1].size()
    assert "background-color" in buttons[0].styleSheet()
    assert "border-radius" in buttons[0].styleSheet()


def testMainMenuBarIsAvailableWithFileAndViewMenus(qtbot) -> None:  # type: ignore[no-untyped-def]

    window = _mainWindowCreate()
    qtbot.addWidget(window)

    assert [action.text() for action in window.menuBar().actions()] == ["&File", "&View"]


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
        "completeForward",
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
            "Complete Forward",
            "Attacking Midfielder",
            "Box-to-Box Midfielder",
            "Defensive Midfielder",
            "Centre-Back",
            "Sweeper Keeper",
        }
    ]

    assert "Roles (6)" in labels
    assert roleNames == [
        "Complete Forward",
        "Attacking Midfielder",
        "Box-to-Box Midfielder",
        "Defensive Midfielder",
        "Centre-Back",
        "Sweeper Keeper",
    ]
    assert "Ball-Playing Goalkeeper" not in labels


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
