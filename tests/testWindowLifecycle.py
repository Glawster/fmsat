"""Secondary-window lifecycle tests."""

from unittest.mock import Mock

from PySide6.QtWidgets import QMessageBox

from fmsat.app.managementWindow import ManagementWindow
from fmsat.app.window import MainWindow


def _mainWindowCreate() -> MainWindow:
    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    return MainWindow(Mock(), database, (), Mock(), Mock(), Mock())


def testManagementWindowIsOwnedAndClosedByMainWindow(qtbot) -> None:  # type: ignore[no-untyped-def]
    window = _mainWindowCreate()
    qtbot.addWidget(window)

    window.managementShow("Tactics")
    managementWindow = window.managementWindow

    assert managementWindow is not None
    assert managementWindow.parent() is window
    assert managementWindow.isVisible()

    window.close()

    assert not managementWindow.isVisible()


def testManagementWindowClosesItsScreenshotViewers(qtbot) -> None:  # type: ignore[no-untyped-def]
    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    window = ManagementWindow(database, Mock())
    viewer = Mock()
    window.screenshotWindows.append(viewer)
    qtbot.addWidget(window)

    window.close()

    viewer.close.assert_called_once_with()


def testSuccessfulDeletionUsesStatusMessageWithoutCompletionDialog(
    qtbot, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    database.tacticsDelete.return_value = Mock(deletedCount=1, imageFilenames=())
    screenshotStore = Mock()
    screenshotStore.capturesRemove.return_value = []
    completionDialog = Mock()
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(QMessageBox, "information", completionDialog)
    window = ManagementWindow(database, screenshotStore)
    qtbot.addWidget(window)

    window._deleteFinish("tactic", ["High Press"])

    completionDialog.assert_not_called()
    assert "Deleted 1 tactic" in window.statusBar().currentMessage()
