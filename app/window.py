"""Main window and spreadsheet-style screenshot review."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QImage
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from fmsat.core.config import AttributeDefinition
from fmsat.core.parser import ExtractedPlayer
from fmsat.core.requirements import ScreenshotPlan, TacticScreenshotPlanner
from fmsat.core.services import ImportError, ImportResult, ScreenshotImportService
from fmsat.core.validation import PlayerValidator
from fmsat.database import Database, DatabaseError

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """FMSAT main window for importing, reviewing, and confirming player data."""

    baseColumns = ("Name", "Positions", "CA", "PA")

    def __init__(
        self,
        importService: ScreenshotImportService,
        database: Database,
        attributes: tuple[AttributeDefinition, ...],
        validator: PlayerValidator,
        screenshotPlanner: TacticScreenshotPlanner,
    ) -> None:
        super().__init__()
        self.importService = importService
        self.database = database
        self.attributes = attributes
        self.validator = validator
        self.screenshotPlanner = screenshotPlanner
        self.currentResult: ImportResult | None = None
        self.currentTactic: str | None = None
        self.setWindowTitle("Football Manager Squad Assessment Tool")
        self.resize(1500, 800)
        self._actionsCreate()
        self._menuCreate()
        self._toolbarCreate()
        self._contentCreate()
        self.statusBar().showMessage("Ready — copy a screenshot or choose Import Screenshot")

    def clipboardImport(self) -> bool:
        """Import the current clipboard image, returning whether one was present."""

        image = QApplication.clipboard().image()
        if image.isNull():
            return False
        self._imageImport(self._qImageConvert(image), "clipboard")
        return True

    def fileImport(self) -> None:
        """Use a clipboard image when available, otherwise ask for a file."""

        tacticName = self._tacticSelect()
        if tacticName is None:
            return
        try:
            captured = self.database.screenTypesForTactic(tacticName)
        except DatabaseError as exc:
            self._errorShow("Database error", str(exc))
            return
        plan = self.screenshotPlanner.plan(tacticName, captured)
        if not self._screenshotPrompt(plan):
            return
        self.currentTactic = tacticName
        if self.clipboardImport():
            return
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import Squad Attributes Screenshot",
            str(Path.home()),
            "Screenshots (*.png *.jpg *.jpeg)",
        )
        if not filename:
            return
        self.statusBar().showMessage(f"Importing {Path(filename).name}…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = self.importService.fileImport(Path(filename))
            self._resultShow(result)
        except (ImportError, OSError) as exc:
            self._errorShow("Import failed", str(exc))
        finally:
            QApplication.restoreOverrideCursor()

    def playersShow(self) -> None:
        """Show a concise list of player records stored locally."""

        try:
            players = self.database.playersList()
        except DatabaseError as exc:
            self._errorShow("Database error", str(exc))
            return
        if not players:
            QMessageBox.information(self, "Players", "No confirmed players have been saved yet.")
            return
        lines = [
            f"{player.name} — {player.positions or 'No position'} "
            f"(CA {player.ca or '—'}, PA {player.pa or '—'})"
            for player in players[:100]
        ]
        QMessageBox.information(self, "Players", "\n".join(lines))

    def reviewSave(self) -> None:
        """Read corrected cells and persist the reviewed import."""

        if self.currentResult is None:
            return
        if self.currentTactic is None:
            self._errorShow("Cannot save", "Select a tactic before saving this screenshot")
            return
        players = self._tablePlayersRead()
        missingNames = [
            index + 1 for index, player in enumerate(players) if not player.name.strip()
        ]
        if missingNames:
            QMessageBox.warning(
                self,
                "Cannot save",
                f"Player name is required on row(s): {', '.join(map(str, missingNames))}",
            )
            return
        try:
            session = self.database.importSave(
                self.currentResult.source,
                self.currentResult.screenType,
                players,
                self.currentTactic,
            )
        except DatabaseError as exc:
            self._errorShow("Database error", str(exc))
            return
        self.saveAction.setEnabled(False)
        self.statusBar().showMessage(
            f"Saved {self.currentTactic}: import {session.id} with {len(players)} player(s)",
            8000,
        )

    def settingsShow(self) -> None:
        """Describe the Phase 1 configuration location."""

        QMessageBox.information(
            self,
            "Settings",
            "Phase 1 settings are stored in fmsat/config/*.yaml.\n"
            f"Low-confidence threshold: {self.validator.confidenceThreshold:.0%}",
        )

    def _actionsCreate(self) -> None:
        self.importAction = QAction("Import Screenshot", self)
        self.importAction.setShortcut("Ctrl+I")
        self.importAction.triggered.connect(self.fileImport)
        self.databaseAction = QAction("Database", self)
        self.databaseAction.triggered.connect(self.playersShow)
        self.playersAction = QAction("Players", self)
        self.playersAction.triggered.connect(self.playersShow)
        self.settingsAction = QAction("Settings", self)
        self.settingsAction.triggered.connect(self.settingsShow)
        self.saveAction = QAction("Save Confirmed Data", self)
        self.saveAction.setShortcut("Ctrl+S")
        self.saveAction.setEnabled(False)
        self.saveAction.triggered.connect(self.reviewSave)
        self.exitAction = QAction("Exit", self)
        self.exitAction.triggered.connect(self.close)

    def _contentCreate(self) -> None:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        self.instructions = QLabel(
            "Import a Squad Attributes screenshot. Extracted cells remain editable until saved."
        )
        layout.addWidget(self.instructions)
        self.table = QTableWidget(0, len(self.baseColumns) + len(self.attributes) + 1)
        headers = [
            *self.baseColumns,
            *(attribute.abbreviation for attribute in self.attributes),
            "Confidence",
        ]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        self.setCentralWidget(widget)

    def _errorShow(self, title: str, message: str) -> None:
        logger.warning("%s: %s", title, message)
        self.statusBar().showMessage(message, 10000)
        QMessageBox.critical(self, title, message)

    def _imageImport(self, image: np.ndarray, source: str) -> None:
        self.statusBar().showMessage("Importing clipboard screenshot…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._resultShow(self.importService.imageImport(image, source))
        except ImportError as exc:
            self._errorShow("Import failed", str(exc))
        finally:
            QApplication.restoreOverrideCursor()

    def _menuCreate(self) -> None:
        fileMenu = self.menuBar().addMenu("&File")
        fileMenu.addAction(self.importAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.exitAction)
        viewMenu = self.menuBar().addMenu("&View")
        viewMenu.addAction(self.databaseAction)
        viewMenu.addAction(self.playersAction)
        viewMenu.addAction(self.settingsAction)

    def _qImageConvert(self, image: QImage) -> np.ndarray:
        converted = image.convertToFormat(QImage.Format.Format_RGB888)
        array = np.frombuffer(converted.bits(), dtype=np.uint8).reshape(
            converted.height(), converted.bytesPerLine()
        )
        rgb = array[:, : converted.width() * 3].reshape(converted.height(), converted.width(), 3)
        return rgb[:, :, ::-1].copy()

    def _resultShow(self, result: ImportResult) -> None:
        self.currentResult = result
        self.table.setRowCount(len(result.players))
        for row, player in enumerate(result.players):
            values = [
                player.name,
                player.positions,
                player.ca,
                player.pa,
                *(
                    ""
                    if player.attributes.get(attribute.name) is None
                    else str(player.attributes[attribute.name])
                    for attribute in self.attributes
                ),
                f"{player.confidence:.1%}",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == len(values) - 1:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if self.validator.isLowConfidence(player):
                    item.setBackground(QColor("#fff1b8"))
                    item.setToolTip(
                        "OCR confidence below "
                        f"{self.validator.confidenceThreshold:.0%}; review this row"
                    )
                self.table.setItem(row, column, item)
        self.saveAction.setEnabled(True)
        self.statusBar().showMessage(
            f"Extracted {len(result.players)} player(s) for {self.currentTactic} — "
            "review highlighted rows before saving"
        )

    def _screenshotPrompt(self, plan: ScreenshotPlan) -> bool:
        """Explain the next required capture or offer an update override."""

        if plan.isComplete:
            message = QMessageBox(self)
            message.setWindowTitle("Tactic already recognised")
            message.setIcon(QMessageBox.Icon.Information)
            message.setText(
                f"{plan.tacticName} is already recognised. All required screenshots "
                "are stored, so you do not need to take them again."
            )
            updateButton = message.addButton("Update Screenshot", QMessageBox.ButtonRole.AcceptRole)
            message.addButton("Use Existing", QMessageBox.ButtonRole.RejectRole)
            message.exec()
            return message.clickedButton() is updateButton

        checklist = "\n\n".join(
            f"• {requirement.title}\n  {requirement.instructions}" for requirement in plan.missing
        )
        QMessageBox.information(
            self,
            f"Screenshots needed for {plan.tacticName}",
            "Please take the following screenshot before continuing:\n\n" + checklist,
        )
        return True

    def _tacticSelect(self) -> str | None:
        """Ask for a tactic while reusing locally recognised names where possible."""

        try:
            tactics = self.database.tacticsList()
        except DatabaseError as exc:
            self._errorShow("Database error", str(exc))
            return None
        if tactics:
            name, accepted = QInputDialog.getItem(
                self,
                "Select tactic",
                "Choose a recognised tactic or enter a new tactic name:",
                tactics,
                0,
                True,
            )
        else:
            name, accepted = QInputDialog.getText(
                self,
                "Name tactic",
                "Enter the tactic name used for this screenshot:",
            )
        cleanName = name.strip()
        if not accepted:
            return None
        if not cleanName:
            QMessageBox.warning(self, "Tactic name required", "Enter a tactic name to continue.")
            return None
        return cleanName

    def _tablePlayersRead(self) -> list[ExtractedPlayer]:
        if self.currentResult is None:
            return []
        players: list[ExtractedPlayer] = []
        for row in range(self.table.rowCount()):
            original = self.currentResult.players[row]
            attributes: dict[str, int | None] = {}
            for offset, definition in enumerate(self.attributes, start=4):
                text = self.table.item(row, offset).text().strip()
                attributes[definition.name] = int(text) if text.isdigit() else None
            players.append(
                ExtractedPlayer(
                    name=self.table.item(row, 0).text(),
                    positions=self.table.item(row, 1).text(),
                    ca=self.table.item(row, 2).text(),
                    pa=self.table.item(row, 3).text(),
                    attributes=attributes,
                    confidence=original.confidence,
                )
            )
        return players

    def _toolbarCreate(self) -> None:
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        for action in (
            self.importAction,
            self.databaseAction,
            self.playersAction,
            self.settingsAction,
            self.saveAction,
        ):
            toolbar.addAction(action)
        self.addToolBar(toolbar)
