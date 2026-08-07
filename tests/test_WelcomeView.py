"""Welcome workspace behaviour tests."""

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtWidgets import QLabel, QTableWidget, QToolButton

from fmsat.app.welcomeView import WelcomeService, WelcomeView
from fmsat.app.window import MainWindow


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
