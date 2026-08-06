"""Tactic and squad data-management screens."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.screenshotWindow import ScreenshotWindow
from fmsat.core.screenshotStore import ScreenshotStore
from fmsat.database import Database, DatabaseError


class ManagementWindow(QMainWindow):
    """Manage stored tactics, squads, players, captures, and safe deletion."""

    def __init__(
        self,
        database: Database,
        screenshotStore: ScreenshotStore,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.database = database
        self.screenshotStore = screenshotStore
        self.screenshotWindows: list[ScreenshotWindow] = []
        self.setWindowTitle("FMSAT Data Management")
        self.resize(1100, 760)
        self.tabs = QTabWidget()
        self.tacticTab = self._tacticTabCreate()
        self.squadTab = self._squadTabCreate()
        self.tabs.addTab(self.tacticTab, "Tactics")
        self.tabs.addTab(self.squadTab, "Squads")
        self.setCentralWidget(self.tabs)
        self.dataRefresh()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Close screenshot viewers owned by this management window."""

        for viewer in tuple(self.screenshotWindows):
            viewer.close()
        super().closeEvent(event)

    def dataRefresh(self) -> None:
        """Reload tactic and squad lists from committed database state."""

        selectedSquad = None
        currentSquadRow = self.squadTable.currentRow()
        if currentSquadRow >= 0:
            currentSquadItem = self.squadTable.item(currentSquadRow, 1)
            if currentSquadItem is not None:
                selectedSquad = currentSquadItem.text()
        try:
            tacticRecords = self.database.tacticRecords()
            squadRecords = self.database.squadRecords()
        except DatabaseError as exc:
            QMessageBox.critical(self, "Database error", str(exc))
            return
        self.tacticTable.setRowCount(len(tacticRecords))
        for row, record in enumerate(tacticRecords):
            selected = QTableWidgetItem()
            selected.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
            )
            selected.setCheckState(Qt.CheckState.Unchecked)
            self.tacticTable.setItem(row, 0, selected)
            thumbnail = QTableWidgetItem("No Formation image")
            if record.formationImage and Path(record.formationImage).is_file():
                pixmap = QPixmap(record.formationImage).scaled(
                    280,
                    160,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                thumbnail.setText("")
                thumbnail.setIcon(QIcon(pixmap))
            self.tacticTable.setItem(row, 1, thumbnail)
            self.tacticTable.setItem(row, 2, QTableWidgetItem(record.name))
            self.tacticTable.setItem(row, 3, QTableWidgetItem(str(record.captureCount)))
            self.tacticTable.setRowHeight(row, 172)

        self.squadTable.setRowCount(len(squadRecords))
        for row, record in enumerate(squadRecords):
            selected = QTableWidgetItem()
            selected.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
            )
            selected.setCheckState(Qt.CheckState.Unchecked)
            self.squadTable.setItem(row, 0, selected)
            self.squadTable.setItem(row, 1, QTableWidgetItem(record.name))
            self.squadTable.setItem(row, 2, QTableWidgetItem(str(record.captureCount)))
            self.squadTable.setItem(row, 3, QTableWidgetItem(str(record.playerCount)))
        self.playerTable.setRowCount(0)
        if selectedSquad is not None:
            for row in range(self.squadTable.rowCount()):
                if self.squadTable.item(row, 1).text() == selectedSquad:
                    self.squadTable.selectRow(row)
                    self.squadTable.setCurrentCell(row, 1)
                    self._playersRefresh()
                    break
        self._selectionRefresh()

    def tabShow(self, name: str) -> None:
        """Select a management tab by its visible name."""

        self.tabs.setCurrentIndex(0 if name == "Tactics" else 1)

    def _buttonsCreate(
        self,
        table: QTableWidget,
        deleteAction: Callable[[], None],
    ) -> tuple[QHBoxLayout, QPushButton]:
        buttons = QHBoxLayout()
        selectAll = QPushButton("Select all")
        selectAll.clicked.connect(lambda: self._checksSet(table, Qt.CheckState.Checked))
        buttons.addWidget(selectAll)
        clear = QPushButton("Clear selection")
        clear.clicked.connect(lambda: self._checksSet(table, Qt.CheckState.Unchecked))
        buttons.addWidget(clear)
        buttons.addStretch()
        deleteButton = QPushButton("Delete selected")
        deleteButton.setEnabled(False)
        deleteButton.clicked.connect(deleteAction)
        buttons.addWidget(deleteButton)
        return buttons, deleteButton

    def _checksSet(self, table: QTableWidget, state: Qt.CheckState) -> None:
        for row in range(table.rowCount()):
            table.item(row, 0).setCheckState(state)
        self._selectionRefresh()

    def _deleteConfirm(self, kind: str, names: list[str]) -> bool:
        if not names:
            QMessageBox.information(self, "Nothing selected", f"Select at least one {kind}.")
            return False
        answer = QMessageBox.question(
            self,
            f"Delete selected {kind}s",
            f"Delete {len(names)} selected {kind}(s)?\n\n" + "\n".join(names),
        )
        return answer == QMessageBox.StandardButton.Yes

    def _deleteFinish(self, kind: str, names: list[str]) -> None:
        if not self._deleteConfirm(kind, names):
            return
        try:
            result = (
                self.database.tacticsDelete(names)
                if kind == "tactic"
                else self.database.squadsDelete(names)
            )
        except DatabaseError as exc:
            QMessageBox.critical(self, "Database error", str(exc))
            return
        failures = self.screenshotStore.capturesRemove(list(result.imageFilenames))
        ownedData = (
            "capture records and player data" if kind == "squad" else "capture records"
        )
        message = (
            f"Deleted {result.deletedCount} {kind}(s), including associated "
            f"{ownedData}."
        )
        if failures:
            paths = "\n".join(str(path) for path in failures)
            message += (
                "\n\nThe database deletion is complete, but these referenced files "
                f"were not removed and may still exist:\n{paths}"
            )
            QMessageBox.warning(self, "Deleted; file cleanup needed", message)
        else:
            self.statusBar().showMessage(message, 6000)
        self.dataRefresh()

    def _playerMenuShow(self, point) -> None:  # type: ignore[no-untyped-def]
        item = self.playerTable.itemAt(point)
        if item is None:
            return
        path = self.playerTable.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        action = QAction("Show Screenshot", menu)
        action.triggered.connect(lambda: self._screenshotShow(str(path)))
        menu.addAction(action)
        menu.exec(self.playerTable.viewport().mapToGlobal(point))

    def _playersRefresh(self) -> None:
        row = self.squadTable.currentRow()
        if row < 0:
            self.playerTable.setRowCount(0)
            return
        squadName = self.squadTable.item(row, 1).text()
        try:
            records = self.database.squadPlayerRecords(squadName)
        except DatabaseError as exc:
            QMessageBox.critical(self, "Database error", str(exc))
            return
        self.playerTable.setRowCount(len(records))
        for playerRow, record in enumerate(records):
            values = (
                record.name,
                record.positions,
                record.ca,
                record.pa,
                f"{record.confidence:.1%}",
                record.importedAt.strftime("%Y-%m-%d %H:%M"),
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, record.imageFilename)
                self.playerTable.setItem(playerRow, column, cell)

    def _screenshotShow(self, path: str) -> None:
        viewer = ScreenshotWindow.pathOpen(path, self)
        if viewer is not None:
            self.screenshotWindows.append(viewer)
            viewer.destroyed.connect(lambda: self._viewerForget(viewer))

    def _selectionRefresh(self) -> None:
        tacticCount = len(self._selectedNames(self.tacticTable, 2))
        squadCount = len(self._selectedNames(self.squadTable, 1))
        self.tacticSelection.setText(f"{tacticCount} selected")
        self.squadSelection.setText(f"{squadCount} selected")
        self.tacticDeleteButton.setEnabled(tacticCount > 0)
        self.squadDeleteButton.setEnabled(squadCount > 0)
        self.squadCleanButton.setEnabled(squadCount > 0)

    def _squadsClean(self) -> None:
        names = self._selectedNames(self.squadTable, 1)
        if not names:
            return
        try:
            results = [(name, self.database.squadClean(name)) for name in names]
        except DatabaseError as exc:
            QMessageBox.critical(self, "Database error", str(exc))
            return
        corrected = sum(result.correctedCount for _, result in results)
        merged = sum(result.mergedCount for _, result in results)
        ambiguous = sum(result.ambiguousCount for _, result in results)
        message = (
            f"Cleaned {len(results)} squad(s): corrected {corrected} field(s) and "
            f"merged {merged} unambiguous duplicate player(s)."
        )
        if ambiguous:
            message += (
                f" {ambiguous} possible duplicate(s) were retained for later review."
            )
            QMessageBox.warning(self, "Squad cleanup needs review", message)
        else:
            self.statusBar().showMessage(message, 8000)
        self.dataRefresh()

    @staticmethod
    def _selectedNames(table: QTableWidget, nameColumn: int) -> list[str]:
        return [
            table.item(row, nameColumn).text()
            for row in range(table.rowCount())
            if table.item(row, 0).checkState() == Qt.CheckState.Checked
        ]

    def _squadTabCreate(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.squadTable = QTableWidget(0, 4)
        self.squadTable.setHorizontalHeaderLabels(("Select", "Squad", "Captures", "Players"))
        squadHeader = self.squadTable.horizontalHeader()
        squadHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for column in range(1, 4):
            squadHeader.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        self.squadTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.squadTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.squadTable.itemSelectionChanged.connect(self._playersRefresh)
        self.squadTable.itemChanged.connect(self._selectionRefresh)
        layout.addWidget(self.squadTable, 1)
        buttonLayout, self.squadDeleteButton = self._buttonsCreate(
            self.squadTable,
            lambda: self._deleteFinish("squad", self._selectedNames(self.squadTable, 1)),
        )
        self.squadSelection = QPushButton("0 selected")
        self.squadSelection.setEnabled(False)
        buttonLayout.insertWidget(2, self.squadSelection)
        self.squadCleanButton = QPushButton("Clean selected")
        self.squadCleanButton.setEnabled(False)
        self.squadCleanButton.clicked.connect(self._squadsClean)
        buttonLayout.insertWidget(buttonLayout.count() - 1, self.squadCleanButton)
        layout.addLayout(buttonLayout)
        self.playerTable = QTableWidget(0, 6)
        self.playerTable.setHorizontalHeaderLabels(
            ("Player", "Positions", "CA", "PA", "Confidence", "Imported")
        )
        playerHeader = self.playerTable.horizontalHeader()
        playerHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        playerHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in range(2, 5):
            playerHeader.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        playerHeader.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.playerTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.playerTable.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playerTable.customContextMenuRequested.connect(self._playerMenuShow)
        layout.addWidget(self.playerTable, 3)
        return tab

    def _tacticTabCreate(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.tacticTable = QTableWidget(0, 4)
        self.tacticTable.setHorizontalHeaderLabels(("Select", "Formation", "Tactic", "Captures"))
        self.tacticTable.setIconSize(QPixmap(280, 160).size())
        header = self.tacticTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tacticTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tacticTable.itemChanged.connect(self._selectionRefresh)
        layout.addWidget(self.tacticTable)
        self.tacticSelection = QPushButton("0 selected")
        self.tacticSelection.setEnabled(False)
        buttonLayout, self.tacticDeleteButton = self._buttonsCreate(
            self.tacticTable,
            lambda: self._deleteFinish("tactic", self._selectedNames(self.tacticTable, 2)),
        )
        buttonLayout.insertWidget(2, self.tacticSelection)
        layout.addLayout(buttonLayout)
        return tab

    def _viewerForget(self, viewer: ScreenshotWindow) -> None:
        if viewer in self.screenshotWindows:
            self.screenshotWindows.remove(viewer)
