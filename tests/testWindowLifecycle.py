"""Secondary-window lifecycle tests."""

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QPushButton,
)

from fmsat.app.managementWindow import ManagementWindow
from fmsat.app.window import MainWindow
from fmsat.core.config import AttributeDefinition
from fmsat.core.detection import ScreenType
from fmsat.core.parser import ExtractedPlayer
from fmsat.core.services import ImportError as ScreenshotImportError
from fmsat.core.services import ImportResult
from fmsat.core.validation import PlayerValidator


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


def testCleanSelectedSquadRunsPersistedCleanup(qtbot) -> None:  # type: ignore[no-untyped-def]
    database = Mock()
    database.tacticRecords.return_value = []
    squad = SimpleNamespace(name="First Team", captureCount=4, playerCount=81)
    database.squadRecords.side_effect = [[squad], [squad]]
    player = SimpleNamespace(
        name="Max Power",
        positions="DM, M (C)",
        ca="114",
        pa="130",
        confidence=0.98,
        importedAt=SimpleNamespace(strftime=lambda _format: "2026-08-06 10:00"),
        imageFilename="capture.png",
    )
    database.squadPlayerRecords.return_value = [player]
    database.squadClean.return_value = Mock(
        correctedCount=3,
        mergedCount=30,
        ambiguousCount=0,
        remainingCount=51,
    )
    window = ManagementWindow(database, Mock())
    qtbot.addWidget(window)
    window.squadTable.selectRow(0)
    window.squadTable.item(0, 0).setCheckState(Qt.CheckState.Checked)
    database.squadPlayerRecords.reset_mock()

    window._squadsClean()

    database.squadClean.assert_called_once_with("First Team")
    database.squadPlayerRecords.assert_called_with("First Team")
    assert window.playerTable.rowCount() == 1
    assert window.playerTable.item(0, 0).text() == "Max Power"
    assert "merged 30" in window.statusBar().currentMessage()


def testSquadReviewShowsOnlyCollectedAttributeColumns(qtbot) -> None:  # type: ignore[no-untyped-def]
    attributes = (
        AttributeDefinition("passing", "Pas", 1),
        AttributeDefinition("vision", "Vis", 2),
        AttributeDefinition("long_throws", "Lon", 3),
    )
    validator = PlayerValidator()
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


def testAdaptiveSquadCaptureUsesGenericChoices(qtbot, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    window = _mainWindowCreate()
    qtbot.addWidget(window)
    labels: list[str] = []

    def dialogInspect(dialog: QDialog) -> int:
        labels.extend(button.text() for button in dialog.findChildren(QPushButton))
        return 0

    monkeypatch.setattr(QDialog, "exec", dialogInspect)

    assert window._squadCaptureChoice(3) == "cancel"
    assert labels == [
        "Cancel import",
        "Capture another screenshot",
        "Finish import",
    ]


def testEmptyClipboardPromptsForScreenshotInsteadOfFile(qtbot, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    window = _mainWindowCreate()
    qtbot.addWidget(window)
    clipboard = Mock()
    clipboard.image.return_value = QImage()
    monkeypatch.setattr(QApplication, "clipboard", lambda: clipboard)
    window._screenshotReadyWait = Mock(return_value=False)

    result = window._screenshotAcquire(
        ScreenType.SQUAD_ATTRIBUTES,
        "Import Squad Attributes, Capture 1",
    )

    assert result is None
    window._screenshotReadyWait.assert_called_once_with(
        "Take screenshot",
        "Take the requested import squad attributes, capture 1 and leave it on the clipboard.",
        allowBack=True,
        backText="Cancel",
    )


def testMissingPlayerRowsPromptsForImmediateRetake(qtbot, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    importService = Mock()
    imported = ImportResult(
        "clipboard",
        ScreenType.SQUAD_ATTRIBUTES,
        [ExtractedPlayer("Max Power", "DM", "114", "130", {}, 0.98)],
    )
    importService.imageImport.side_effect = [
        ScreenshotImportError(
            "No player rows could be extracted. Please retake the screenshot."
        ),
        imported,
    ]
    window = MainWindow(importService, Mock(), (), Mock(), Mock(), Mock())
    qtbot.addWidget(window)
    clipboard = Mock()
    clipboard.image.return_value = QImage(10, 10, QImage.Format.Format_RGB32)
    monkeypatch.setattr(QApplication, "clipboard", lambda: clipboard)
    window._screenshotPreview = Mock(return_value="use")
    window._screenshotReadyWait = Mock(return_value=True)

    result = window._screenshotAcquire(
        ScreenType.SQUAD_ATTRIBUTES,
        "Import Squad Attributes, Capture 1",
    )

    assert result is imported
    window._screenshotReadyWait.assert_called_once_with(
        "Please retake screenshot",
        "No player rows could be extracted. Please retake the screenshot.",
        allowBack=True,
        backText="Cancel",
    )


def testExistingSquadIsDefaultImportChoice(qtbot, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    window = _mainWindowCreate()
    qtbot.addWidget(window)
    window.database.squadsList.return_value = ["bcafc", "Under 21s"]
    observed: dict[str, object] = {}

    def itemSelect(parent, title, prompt, choices, selectedIndex, editable):  # type: ignore[no-untyped-def]
        observed["choices"] = choices
        observed["selectedIndex"] = selectedIndex
        return choices[selectedIndex], True

    monkeypatch.setattr(QInputDialog, "getItem", itemSelect)

    assert window._squadSelect() == "bcafc"
    assert observed == {
        "choices": ["bcafc", "Under 21s", "Create new squad…"],
        "selectedIndex": 0,
    }


def testExistingSquadImportAppendsAfterStoredPlayers(qtbot) -> None:  # type: ignore[no-untyped-def]
    window = _mainWindowCreate()
    qtbot.addWidget(window)
    window.database.squadsList.return_value = ["bcafc"]
    window.database.playerNamesForSquad.return_value = {"Sam Walker", "Joe Wright"}
    window._squadSelect = Mock(return_value="bcafc")
    window._screenshotAcquire = Mock(return_value=None)

    window.squadImport()

    assert window.currentSquadExistingNames == {"sam walker", "joe wright"}
    assert window.currentSquadPlayerOffset == 2
