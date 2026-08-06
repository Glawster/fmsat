"""Secondary-window lifecycle tests."""

from unittest.mock import Mock

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QDialog, QHeaderView, QMessageBox, QPushButton

from fmsat.app.managementWindow import ManagementWindow
from fmsat.app.window import MainWindow
from fmsat.core.config import AttributeDefinition
from fmsat.core.detection import ScreenType
from fmsat.core.parser import ExtractedPlayer
from fmsat.core.services import ImportResult


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


def testTacticTableUsesWideColumnsAndLargeFormationRows(qtbot) -> None:  # type: ignore[no-untyped-def]
    database = Mock()
    tactic = Mock()
    tactic.name = "High Press"
    tactic.formationImage = None
    tactic.captureCount = 3
    database.tacticRecords.return_value = [tactic]
    database.squadRecords.return_value = []
    window = ManagementWindow(database, Mock())
    qtbot.addWidget(window)
    header = window.tacticTable.horizontalHeader()

    assert window.tacticTable.iconSize() == QSize(280, 160)
    assert window.tacticTable.rowHeight(0) == 172
    assert header.sectionResizeMode(1) is QHeaderView.ResizeMode.Stretch
    assert header.sectionResizeMode(2) is QHeaderView.ResizeMode.Stretch


def testSquadListUsesOneQuarterOfAvailableTableSpace(qtbot) -> None:  # type: ignore[no-untyped-def]
    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    window = ManagementWindow(database, Mock())
    qtbot.addWidget(window)
    layout = window.squadTab.layout()

    assert layout.stretch(0) == 1
    assert layout.stretch(2) == 3


def testSquadManagementTablesUseFullPaneWidth(qtbot) -> None:  # type: ignore[no-untyped-def]
    database = Mock()
    database.tacticRecords.return_value = []
    database.squadRecords.return_value = []
    window = ManagementWindow(database, Mock())
    qtbot.addWidget(window)
    squadHeader = window.squadTable.horizontalHeader()
    playerHeader = window.playerTable.horizontalHeader()

    assert squadHeader.sectionResizeMode(0) is QHeaderView.ResizeMode.ResizeToContents
    assert all(
        squadHeader.sectionResizeMode(column) is QHeaderView.ResizeMode.Stretch
        for column in range(1, 4)
    )
    assert playerHeader.sectionResizeMode(0) is QHeaderView.ResizeMode.Stretch
    assert playerHeader.sectionResizeMode(1) is QHeaderView.ResizeMode.Stretch
    assert playerHeader.sectionResizeMode(5) is QHeaderView.ResizeMode.Stretch


def testSquadReviewShowsOnlyCollectedAttributeColumns(qtbot) -> None:  # type: ignore[no-untyped-def]
    attributes = (
        AttributeDefinition("passing", "Pas", 1),
        AttributeDefinition("vision", "Vis", 2),
        AttributeDefinition("long_throws", "Lon", 3),
    )
    validator = Mock()
    validator.isLowConfidence.return_value = False
    window = MainWindow(Mock(), Mock(), attributes, validator, Mock(), Mock())
    qtbot.addWidget(window)
    result = ImportResult(
        "clipboard",
        ScreenType.SQUAD_ATTRIBUTES,
        [
            ExtractedPlayer(
                "Max Power",
                "DM",
                "114",
                "130",
                {"passing": 12, "vision": None},
                0.98,
            )
        ],
    )

    window._resultShow(result)

    headers = [
        window.table.horizontalHeaderItem(column).text()
        for column in range(window.table.columnCount())
    ]
    assert headers == ["Name", "Positions", "CA", "PA", "Pas", "Vis", "Confidence"]
    assert window._tablePlayersRead()[0].attributes == {"passing": 12, "vision": None}


def testAttributeViewTransitionOffersBackButton(qtbot, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    window = _mainWindowCreate()
    qtbot.addWidget(window)
    labels: list[str] = []

    def dialogInspect(dialog: QDialog) -> int:
        labels.extend(button.text() for button in dialog.findChildren(QPushButton))
        return 0

    monkeypatch.setattr(QDialog, "exec", dialogInspect)

    ready = window._screenshotReadyWait(
        "Switch to Attribute View 2",
        "Switch views and take a screenshot.",
        allowBack=True,
    )

    assert not ready
    assert labels == ["Back", "Screenshot ready"]
