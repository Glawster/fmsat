"""Main window and spreadsheet-style screenshot review."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.managementWindow import ManagementWindow
from fmsat.core.config import AttributeDefinition
from fmsat.core.detection import ScreenType
from fmsat.core.parser import ExtractedPlayer
from fmsat.core.requirements import ScreenshotRequirement, TacticScreenshotPlanner
from fmsat.core.screenshotStore import ScreenshotStore, ScreenshotStoreError
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
        screenshotStore: ScreenshotStore,
    ) -> None:
        super().__init__()
        self.importService = importService
        self.database = database
        self.attributes = attributes
        self.validator = validator
        self.screenshotPlanner = screenshotPlanner
        self.screenshotStore = screenshotStore
        self.currentResult: ImportResult | None = None
        self.currentTactic: str | None = None
        self.currentSquad: str | None = None
        self.currentSquadExistingNames: set[str] = set()
        self.currentSquadPlayerOffset = 0
        self.managementWindow: ManagementWindow | None = None
        self.setWindowTitle("Football Manager Squad Assessment Tool")
        self.resize(1500, 800)
        self._actionsCreate()
        self._menuCreate()
        self._toolbarCreate()
        self._contentCreate()
        self.statusBar().showMessage("Ready — choose Import Tactic or Import Squad")

    def squadImport(self) -> None:
        """Import a Squad Attributes screenshot independently of tactics."""

        squadName = self._squadSelect()
        if squadName is None:
            return
        try:
            existingNames = {
                self._playerNameNormalize(name)
                for name in self.database.playerNamesForSquad(squadName)
            }
        except DatabaseError as exc:
            self._errorShow("Database error", str(exc))
            return
        result = self._screenshotAcquire(
            ScreenType.SQUAD_ATTRIBUTES,
            "Import Squad Attributes Screenshot",
        )
        if result is None:
            return
        newPlayers: list[ExtractedPlayer] = []
        seenNames = set(existingNames)
        for player in result.players:
            normalizedName = self._playerNameNormalize(player.name)
            if normalizedName and normalizedName not in seenNames:
                newPlayers.append(player)
                seenNames.add(normalizedName)
        skipped = len(result.players) - len(newPlayers)
        result.players = newPlayers
        if not result.players:
            QMessageBox.information(
                self,
                "No new squad members",
                f"Every recognised player is already stored for {squadName}.",
            )
            return
        self.currentSquad = squadName
        self.currentSquadExistingNames = existingNames
        self.currentSquadPlayerOffset = len(existingNames)
        self._resultShow(result)
        if skipped:
            self.statusBar().showMessage(
                f"Found {len(newPlayers)} new player(s) for {squadName}; "
                f"skipped {skipped} existing or duplicate row(s). "
                "Correct the editable fields before saving.",
                12000,
            )

    def tacticImport(self) -> None:
        """Import all outstanding screenshots for a new or existing tactic."""

        tacticName = self._tacticSelect(existingOnly=False, includeNew=True)
        if tacticName is None:
            return
        isNewTactic = not tacticName
        captured: set[ScreenType] = set()
        if tacticName:
            try:
                captured = self.database.screenTypesForTactic(tacticName)
            except DatabaseError as exc:
                self._errorShow("Database error", str(exc))
                return
        tacticRequirements = tuple(
            requirement
            for requirement in self.screenshotPlanner.requirements
            if requirement.screenType
            in {
                ScreenType.TACTIC_FORMATION,
                ScreenType.TACTIC_IN_POSSESSION,
                ScreenType.TACTIC_OUT_OF_POSSESSION,
            }
        )
        missing = [item for item in tacticRequirements if item.screenType not in captured]
        if isNewTactic:
            requirementsToImport = missing
        else:
            requirementsToImport = self._tacticCaptureSelect(
                tacticName,
                tacticRequirements,
                missing,
            )
            if requirementsToImport is None:
                return
        for index, requirement in enumerate(requirementsToImport):
            QMessageBox.information(self, requirement.title, requirement.instructions)
            result = self._screenshotAcquire(
                requirement.screenType,
                f"Import {requirement.title}",
            )
            if result is None:
                return
            if requirement.screenType is ScreenType.TACTIC_FORMATION and isNewTactic:
                extractedName = result.tacticName or ""
                confirmedName, accepted = QInputDialog.getText(
                    self,
                    "Confirm tactic name",
                    f"Name extracted at {result.confidence:.1%} confidence:",
                    text=extractedName,
                )
                if not accepted:
                    return
                tacticName = confirmedName.strip()
                if not tacticName:
                    QMessageBox.warning(
                        self,
                        "Tactic name required",
                        "Enter a tactic name to save.",
                    )
                    return
            if not tacticName:
                self._errorShow("Cannot save", "Import the Formation screenshot first")
                return
            self.currentTactic = tacticName
            try:
                screenshotPath = self._screenshotPersist(
                    result,
                    "tactic",
                    tacticName,
                )
            except ScreenshotStoreError as exc:
                self._errorShow("Screenshot storage error", str(exc))
                return
            try:
                session = self.database.tacticImportSave(
                    str(screenshotPath),
                    result.screenType,
                    tacticName,
                )
            except DatabaseError as exc:
                self.screenshotStore.capturesRemove([screenshotPath])
                self._errorShow("Database error", str(exc))
                return
            captured.add(result.screenType)
            remaining = requirementsToImport[index + 1 :]
            outstanding = [
                item for item in tacticRequirements if item.screenType not in captured
            ]
            if remaining:
                nextMessage = f" Next: {remaining[0].title}."
            elif outstanding:
                nextMessage = " Still missing: " + ", ".join(
                    item.title for item in outstanding
                )
                nextMessage += "."
            else:
                nextMessage = " Tactic import is complete."
            self.statusBar().showMessage(
                f"Saved {requirement.title} for {tacticName} "
                f"as import {session.id}.{nextMessage}",
                10000,
            )

    def _tacticCaptureSelect(
        self,
        tacticName: str,
        requirements: tuple[ScreenshotRequirement, ...],
        missing: list[ScreenshotRequirement],
    ) -> list[ScreenshotRequirement] | None:
        """Choose a targeted update or all missing captures for a known tactic."""

        choices: list[tuple[str, list[ScreenshotRequirement]]] = []
        if missing:
            choices.append((f"Complete missing screenshots ({len(missing)})", missing))
        choices.extend((f"Capture {item.title}", [item]) for item in requirements)
        label, accepted = QInputDialog.getItem(
            self,
            "Choose tactic screenshot",
            f"Which screenshot do you want to capture for {tacticName}?",
            [item[0] for item in choices],
            0,
            False,
        )
        if not accepted:
            return None
        return next(items for choiceLabel, items in choices if choiceLabel == label)

    def tacticApplyToSquad(self) -> None:
        """Pair an independently stored squad with a completed tactic."""

        squadName = self._squadSelect(existingOnly=True)
        if squadName is None:
            return
        tacticName = self._tacticSelect(existingOnly=True)
        if tacticName is None:
            return
        requiredTypes = {
            ScreenType.TACTIC_FORMATION,
            ScreenType.TACTIC_IN_POSSESSION,
            ScreenType.TACTIC_OUT_OF_POSSESSION,
        }
        try:
            captured = self.database.screenTypesForTactic(tacticName)
            if not requiredTypes.issubset(captured):
                QMessageBox.information(
                    self,
                    "Complete tactic import first",
                    f"Import all three tactic screenshots for {tacticName} before applying it.",
                )
                return
            application = self.database.tacticApplyToSquad(squadName, tacticName)
        except DatabaseError as exc:
            self._errorShow("Database error", str(exc))
            return
        self.currentSquad = squadName
        self.currentTactic = tacticName
        self.statusBar().showMessage(
            f"Applied {tacticName} to {squadName} (application {application.id})",
            10000,
        )

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

    def managementShow(self, tabName: str) -> None:
        """Open or refresh the non-modal tactic and squad management window."""

        if self.managementWindow is None:
            self.managementWindow = ManagementWindow(
                self.database,
                self.screenshotStore,
                self,
            )
            self.managementWindow.destroyed.connect(self._managementForget)
        else:
            self.managementWindow.dataRefresh()
        self.managementWindow.tabShow(tabName)
        self.managementWindow.show()
        self.managementWindow.raise_()
        self.managementWindow.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Close every secondary FMSAT window with the main application window."""

        if self.managementWindow is not None:
            self.managementWindow.close()
        super().closeEvent(event)

    def reviewSave(self) -> None:
        """Read corrected cells and persist the reviewed import."""

        if self.currentResult is None:
            return
        if self.currentSquad is None:
            self._errorShow("Cannot save", "Name the squad before saving this screenshot")
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
        uniquePlayers: list[ExtractedPlayer] = []
        seenNames = set(self.currentSquadExistingNames)
        for player in players:
            normalizedName = self._playerNameNormalize(player.name)
            if normalizedName not in seenNames:
                uniquePlayers.append(player)
                seenNames.add(normalizedName)
        skipped = len(players) - len(uniquePlayers)
        players = uniquePlayers
        if not players:
            QMessageBox.information(
                self,
                "No new squad members",
                f"Every corrected player is already stored for {self.currentSquad}.",
            )
            return
        try:
            screenshotPath = self._screenshotPersist(
                self.currentResult,
                "squad",
                self.currentSquad,
            )
        except ScreenshotStoreError as exc:
            self._errorShow("Screenshot storage error", str(exc))
            return
        try:
            session = self.database.squadImportSave(
                str(screenshotPath),
                players,
                self.currentSquad,
            )
        except DatabaseError as exc:
            self.screenshotStore.capturesRemove([screenshotPath])
            self._errorShow("Database error", str(exc))
            return
        self.currentResult.source = str(screenshotPath)
        self.saveAction.setEnabled(False)
        self.statusBar().showMessage(
            f"Saved {self.currentSquad}: import {session.id} with {len(players)} new player(s)"
            + (f"; skipped {skipped} existing or duplicate row(s)" if skipped else ""),
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
        self.importTacticAction = QAction("Import Tactic", self)
        self.importTacticAction.setShortcut("Ctrl+T")
        self.importTacticAction.triggered.connect(self.tacticImport)
        self.importSquadAction = QAction("Import Squad", self)
        self.importSquadAction.setShortcut("Ctrl+I")
        self.importSquadAction.triggered.connect(self.squadImport)
        self.applyTacticAction = QAction("Apply Tactic to Squad", self)
        self.applyTacticAction.triggered.connect(self.tacticApplyToSquad)
        self.databaseAction = QAction("Database", self)
        self.databaseAction.triggered.connect(self.playersShow)
        self.playersAction = QAction("Players", self)
        self.playersAction.triggered.connect(self.playersShow)
        self.tacticsAction = QAction("Tactics", self)
        self.tacticsAction.triggered.connect(lambda: self.managementShow("Tactics"))
        self.squadsAction = QAction("Squads", self)
        self.squadsAction.triggered.connect(lambda: self.managementShow("Squads"))
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
            "Import three tactic screenshots, then import a Squad Attributes screenshot. "
            "For each step, take the requested screenshot and leave it on the clipboard; "
            "FMSAT collects it when you continue. Extracted squad cells remain editable "
            "until saved."
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
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        self.saveButton = QPushButton("Save Confirmed Data", self)
        self.saveButton.setEnabled(self.saveAction.isEnabled())
        self.saveButton.clicked.connect(self.saveAction.trigger)
        self.saveAction.changed.connect(
            lambda: self.saveButton.setEnabled(self.saveAction.isEnabled())
        )
        buttonLayout.addWidget(self.saveButton)
        layout.addLayout(buttonLayout)
        self.setCentralWidget(widget)

    def _errorShow(self, title: str, message: str) -> None:
        logger.warning("%s: %s", title, message)
        self.statusBar().showMessage(message, 10000)
        QMessageBox.critical(self, title, message)

    def _screenshotAcquire(
        self,
        expectedType: ScreenType,
        dialogTitle: str,
    ) -> ImportResult | None:
        """Use a clipboard image when available, otherwise ask for a screenshot file."""

        while True:
            clipboardImage = QApplication.clipboard().image()
            image: np.ndarray | None = None
            previewImage = clipboardImage
            source = "clipboard"
            if not clipboardImage.isNull():
                image = self._qImageConvert(clipboardImage)
            else:
                filename, _ = QFileDialog.getOpenFileName(
                    self,
                    dialogTitle,
                    str(Path.home()),
                    "Screenshots (*.png *.jpg *.jpeg)",
                )
                if not filename:
                    return None
                source = filename
                previewImage = QImage(filename)
                if previewImage.isNull():
                    self._errorShow("Import failed", f"Unable to read screenshot: {filename}")
                    return None

            previewChoice = self._screenshotPreview(previewImage, dialogTitle)
            if previewChoice == "use":
                break
            if previewChoice == "cancel":
                return None

            readyDialog = QMessageBox(self)
            readyDialog.setWindowTitle("Take new screenshot")
            readyDialog.setText(
                f"Take a new {dialogTitle.lower()} now and leave it on the clipboard."
            )
            readyDialog.setInformativeText(
                "Return to FMSAT and click Screenshot ready to preview the new image."
            )
            readyDialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            readyButton = readyDialog.button(QMessageBox.StandardButton.Ok)
            readyButton.setText("Screenshot ready")
            readyDialog.exec()

        self.statusBar().showMessage(f"Importing {expectedType.value} screenshot…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if image is not None:
                return self.importService.imageImport(image, expectedType, source)
            return self.importService.fileImport(Path(source), expectedType)
        except (ImportError, OSError) as exc:
            self._errorShow("Import failed", str(exc))
            return None
        finally:
            QApplication.restoreOverrideCursor()

    def _screenshotPreview(self, image: QImage, dialogTitle: str) -> str:
        """Ask the user to confirm the screenshot FMSAT is about to import."""

        preview = QPixmap.fromImage(image).scaled(
            480,
            270,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        dialog = QMessageBox(self)
        dialog.setWindowTitle(f"Confirm {dialogTitle}")
        dialog.setText("FMSAT sees this screenshot:")
        dialog.setInformativeText("Continue only if this is the requested Football Manager screen.")
        dialog.setIconPixmap(preview)
        cancelButton = dialog.addButton(QMessageBox.StandardButton.Cancel)
        retakeButton = dialog.addButton(
            "Take new screenshot",
            QMessageBox.ButtonRole.ActionRole,
        )
        useButton = dialog.addButton("Use screenshot", QMessageBox.ButtonRole.AcceptRole)
        dialog.setDefaultButton(useButton)
        dialog.exec()
        clickedButton = dialog.clickedButton()
        if clickedButton is useButton:
            return "use"
        if clickedButton is retakeButton:
            return "retake"
        if clickedButton is cancelButton:
            return "cancel"
        return "cancel"

    def _screenshotPersist(
        self,
        result: ImportResult,
        ownerType: str,
        ownerName: str,
    ) -> Path:
        """Persist the original image represented by an import result."""

        if result.image is None:
            raise ScreenshotStoreError("The imported screenshot image is unavailable")
        path = self.screenshotStore.captureSave(
            result.image,
            ownerType,
            ownerName,
            result.screenType.value,
        )
        result.source = str(path)
        return path

    def _menuCreate(self) -> None:
        fileMenu = self.menuBar().addMenu("&File")
        fileMenu.addAction(self.importTacticAction)
        fileMenu.addAction(self.importSquadAction)
        fileMenu.addAction(self.applyTacticAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.exitAction)
        viewMenu = self.menuBar().addMenu("&View")
        viewMenu.addAction(self.databaseAction)
        viewMenu.addAction(self.playersAction)
        viewMenu.addAction(self.tacticsAction)
        viewMenu.addAction(self.squadsAction)
        viewMenu.addAction(self.settingsAction)

    def _managementForget(self) -> None:
        self.managementWindow = None

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
        self.table.setVerticalHeaderLabels(
            [
                str(self.currentSquadPlayerOffset + row + 1)
                for row in range(len(result.players))
            ]
        )
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
            f"Extracted {len(result.players)} player(s) for {self.currentSquad} — "
            "review highlighted rows before saving"
        )

    def _tacticSelect(
        self,
        *,
        existingOnly: bool,
        includeNew: bool = False,
    ) -> str | None:
        """Ask for a tactic while reusing locally recognised names where possible."""

        try:
            tactics = self.database.tacticsList()
        except DatabaseError as exc:
            self._errorShow("Database error", str(exc))
            return None
        if existingOnly and not tactics:
            QMessageBox.information(
                self,
                "Import a tactic first",
                "No tactics are stored. Import the three tactic screenshots before the squad.",
            )
            return None
        if tactics:
            choices = (["Import new tactic…"] if includeNew else []) + tactics
            selectedIndex = 0
            if self.currentTactic in choices:
                selectedIndex = choices.index(self.currentTactic)
            name, accepted = QInputDialog.getItem(
                self,
                "Select tactic",
                "Choose a recognised tactic:",
                choices,
                selectedIndex,
                False,
            )
        else:
            return None if existingOnly else ""
        cleanName = name.strip()
        if not accepted:
            return None
        if cleanName == "Import new tactic…":
            return ""
        return cleanName

    def _squadSelect(self, *, existingOnly: bool = False) -> str | None:
        """Select an existing squad name or enter a new one."""

        try:
            squads = self.database.squadsList()
        except DatabaseError as exc:
            self._errorShow("Database error", str(exc))
            return None
        if existingOnly and not squads:
            QMessageBox.information(
                self,
                "Import a squad first",
                "No squads are stored. Choose Import Squad before applying a tactic.",
            )
            return None
        if squads:
            choices = squads if existingOnly else ["Create new squad…", *squads]
            selectedIndex = choices.index(self.currentSquad) if self.currentSquad in choices else 0
            name, accepted = QInputDialog.getItem(
                self,
                "Select squad",
                "Choose an existing squad or create a new one:",
                choices,
                selectedIndex,
                False,
            )
            if accepted and name == "Create new squad…":
                name, accepted = QInputDialog.getText(
                    self,
                    "Name squad",
                    "Enter a name for the new squad:",
                )
        else:
            name, accepted = QInputDialog.getText(
                self,
                "Name squad",
                "Enter a name for this squad:",
            )
        if not accepted:
            return None
        cleanName = name.strip()
        if not cleanName:
            QMessageBox.warning(self, "Squad name required", "Enter a squad name to continue.")
            return None
        return cleanName

    @staticmethod
    def _playerNameNormalize(name: str) -> str:
        """Normalize a player name for overlap comparisons."""

        return " ".join(name.split()).casefold()

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
            self.importTacticAction,
            self.importSquadAction,
            self.applyTacticAction,
            self.databaseAction,
            self.playersAction,
            self.settingsAction,
            self.saveAction,
        ):
            toolbar.addAction(action)
        self.addToolBar(toolbar)
