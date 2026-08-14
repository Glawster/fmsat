"""Main window and spreadsheet-style screenshot review."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import TypeVar

import numpy as np
from fmsat.core.logUtils import getLogger
from PySide6.QtCore import QEventLoop, QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.managementWindow import ManagementWindow
from fmsat.app.tacticDetailMapping import (
    tacticDetailIncompleteModelBuild,
    tacticDetailModelBuild,
)
from fmsat.app.roleProfileDialog import RoleProfileReviewDialog
from fmsat.app.tacticDetailView import TacticDetailView
from fmsat.app.welcomeView import WelcomeService, WelcomeView
from fmsat.core.builder.tacticModelLoader import TacticModelLoader
from fmsat.core.builder.tacticScreenshotExtractor import TacticScreenshotExtractor
from fmsat.core.builder.tacticStore import TacticStore
from fmsat.core.config import AttributeDefinition
from fmsat.core.detection import ScreenType
from fmsat.core.parser import (
    ExtractedPlayer,
    RoleProfileEvidence,
    TacticalPhase,
    TacticVocabulary,
)
from fmsat.core.requirements import ScreenshotRequirement, TacticScreenshotPlanner
from fmsat.core.roleKnowledge import RoleKnowledgeService
from fmsat.core.screenshotStore import ScreenshotStore, ScreenshotStoreError
from fmsat.core.services import (
    ImportError,
    ImportResult,
    ScreenshotImportService,
    squadCapturesMerge,
)
from fmsat.core.validation import PlayerValidator, SquadSanityReport
from fmsat.database import Database, DatabaseError
from fmsat.tactics.tactic import Tactic as ModelTactic

logger = getLogger()
ResultType = TypeVar("ResultType")


class MainWindow(QMainWindow):
    """FMSAT main window for importing, reviewing, and confirming player data."""

    baseColumns = ("Name", "Positions", "CA", "PA")
    dataChanged = Signal()

    def __init__(
        self,
        importService: ScreenshotImportService,
        database: Database,
        attributes: tuple[AttributeDefinition, ...],
        validator: PlayerValidator,
        screenshotPlanner: TacticScreenshotPlanner,
        screenshotStore: ScreenshotStore,
        roleKnowledgeService: RoleKnowledgeService | None = None,
        tacticVocabulary: TacticVocabulary | None = None,
    ) -> None:
        super().__init__()
        self.importService = importService
        self.database = database
        self.attributes = attributes
        self.validator = validator
        self.screenshotPlanner = screenshotPlanner
        self.screenshotStore = screenshotStore
        self.roleKnowledgeService = roleKnowledgeService
        self.tacticVocabulary = tacticVocabulary
        self.tacticModelLoader = TacticModelLoader(database.engine)
        self.tacticScreenshotExtractor = TacticScreenshotExtractor(database.engine)
        self.currentResult: ImportResult | None = None
        self.currentTactic: str | None = None
        self.currentSquad: str | None = None
        self.currentSquadExistingNames: set[str] = set()
        self.currentSquadPlayerOffset = 0
        self.currentDisplayedAttributes: tuple[AttributeDefinition, ...] = ()
        self.currentSanityReport: SquadSanityReport | None = None
        self.managementWindow: ManagementWindow | None = None
        self.setWindowTitle("Football Manager Squad Assessment Tool")
        self.resize(1500, 800)
        self._actionsCreate()
        self._menuCreate()
        self._toolbarCreate()
        self._contentCreate()
        self.dataChanged.connect(self.welcomeView.refresh)
        self.statusBar().showMessage(
            "Ready — choose to Import a Tactic or Squad, or view Tactics or Squads "
            "from the Database."
        )

    def squadImport(self) -> None:
        """Collect arbitrary squad pages and attribute views into one review draft."""

        try:
            existingSquads = self.database.squadsList()
        except DatabaseError as exc:
            self._errorShow("Database error", str(exc))
            return
        squadName = self._squadSelect()
        if squadName is None:
            return
        isNewSquad = squadName.casefold() not in {name.casefold() for name in existingSquads}
        if isNewSquad and not self._squadClubImageCapture(squadName):
            return
        self.currentSquad = squadName
        try:
            existingNames = self.database.playerNamesForSquad(squadName)
        except DatabaseError as exc:
            self._errorShow("Database error", str(exc))
            return
        self.currentSquadExistingNames = {self._playerNameNormalize(name) for name in existingNames}
        self.currentSquadPlayerOffset = len(self.currentSquadExistingNames)
        logger.info(
            "squad import target=%r mode=append existingPlayers=%d",
            squadName,
            self.currentSquadPlayerOffset,
        )
        combined: ImportResult | None = None
        captureNumber = 1
        while True:
            capture = self._screenshotAcquire(
                ScreenType.SQUAD_ATTRIBUTES,
                f"Import Squad Attributes, Capture {captureNumber}",
            )
            if capture is None:
                return
            combined = capture if combined is None else squadCapturesMerge(combined, capture)
            self._resultShow(combined)
            self.saveAction.setEnabled(False)
            QApplication.processEvents()
            while True:
                choice = self._squadCaptureChoice(captureNumber)
                if choice == "cancel":
                    return
                if choice == "finish":
                    break
                if self._screenshotReadyWait(
                    "Capture another squad screenshot",
                    "Show any player page in either attribute view and take a screenshot.",
                    allowBack=True,
                ):
                    captureNumber += 1
                    break
            if choice == "finish":
                break
        if combined is None:
            return
        self.currentResult = combined
        self.saveAction.setEnabled(True)
        if combined.mergeConflicts:
            self.statusBar().showMessage(
                f"Captured {len(combined.players)} players with "
                f"{len(combined.mergeConflicts)} conflicting "
                "value(s); review the combined table before saving.",
                12000,
            )
        else:
            self.statusBar().showMessage(
                f"Captured {len(combined.players)} players from {captureNumber} screenshot(s); "
                "review the combined table before saving.",
                12000,
            )

    def _squadClubImageCapture(self, squadName: str) -> bool:
        """Capture and persist a Club Information screenshot without running OCR."""

        while True:
            if not self._screenshotReadyWait(
                "Capture club badge",
                "Open the club information screen and take a screenshot showing the club badge.",
                allowBack=True,
                backText="Cancel squad import",
            ):
                return False
            clipboardImage = QApplication.clipboard().image()
            if clipboardImage.isNull():
                QMessageBox.warning(
                    self,
                    "Club screenshot unavailable",
                    "No image is currently available on the clipboard.",
                )
                continue
            choice = self._screenshotPreview(clipboardImage, "Club Information")
            if choice == "cancel":
                return False
            if choice == "retake":
                continue
            break

        image = self._qImageConvert(clipboardImage)
        try:
            path = self.screenshotStore.captureSave(
                image,
                "squad",
                squadName,
                ScreenType.CLUB_INFORMATION.value,
            )
            self.database.squadClubImageSave(str(path), squadName)
        except (DatabaseError, ScreenshotStoreError) as exc:
            if "path" in locals():
                self.screenshotStore.capturesRemove([path])
            self._errorShow("Club image error", str(exc))
            return False
        self.dataChanged.emit()
        return True

    def _squadCaptureChoice(self, captureNumber: int) -> str:
        """Choose another arbitrary squad screenshot or finish the draft."""

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Squad screenshot {captureNumber} captured")
        layout = QVBoxLayout(dialog)
        layout.addWidget(
            QLabel(
                "The combined data captured so far is now shown in the review table. "
                "You may capture any player page from either attribute view next."
            )
        )
        choice = "cancel"

        def choiceSet(value: str) -> None:
            nonlocal choice
            choice = value
            dialog.accept()

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancelButton = QPushButton("Cancel import")
        cancelButton.clicked.connect(dialog.reject)
        buttons.addWidget(cancelButton)
        nextButton = QPushButton("Capture another screenshot")
        nextButton.clicked.connect(lambda: choiceSet("continue"))
        buttons.addWidget(nextButton)
        finishButton = QPushButton("Finish import")
        finishButton.clicked.connect(lambda: choiceSet("finish"))
        finishButton.setDefault(True)
        buttons.addWidget(finishButton)
        layout.addLayout(buttons)
        dialog.exec()
        return choice

    def _screenshotReadyWait(
        self,
        title: str,
        instructions: str,
        *,
        allowBack: bool = False,
        backText: str = "Back",
    ) -> bool:
        """Wait while the user prepares the next requested clipboard screenshot."""

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(instructions))
        layout.addWidget(QLabel("Return to FMSAT after taking the screenshot."))
        ready = False

        def readySet() -> None:
            nonlocal ready
            ready = True
            dialog.accept()

        buttons = QHBoxLayout()
        buttons.addStretch()
        if allowBack:
            backButton = QPushButton(backText)
            backButton.clicked.connect(dialog.reject)
            buttons.addWidget(backButton)
        readyButton = QPushButton("Screenshot ready")
        readyButton.clicked.connect(readySet)
        readyButton.setDefault(True)
        buttons.addWidget(readyButton)
        layout.addLayout(buttons)
        dialog.exec()
        return ready

    def tacticImport(self) -> None:
        """Import all outstanding screenshots for a new or existing tactic."""

        self._tacticImportRun()

    def tacticModelImport(self, tacticName: str) -> None:
        """Regenerate one tactic model from saved screenshot evidence."""

        self.tacticProcess(tacticName, forceRebuild=True)

    def tacticProcess(
        self,
        tacticName: str,
        *,
        openDetail: bool = True,
        forceRebuild: bool = False,
    ) -> None:
        """Process one stored tactic into the object model without new screenshots."""

        logger.doing(
            f"{'regenerating' if forceRebuild else 'processing'} tactic model {tacticName}"
        )
        progress = self._tacticProgressCreate()
        progress.show()
        self._progressUpdate(progress, "Loading saved tactic data...", 0)
        try:
            loadResult = self.tacticModelLoader.tacticLoad(tacticName)
            logger.info(f"loaded tactic source: {loadResult.source}")
            logger.value("loaded tactic issues", len(getattr(loadResult, "issues", ())))
            self._progressUpdate(progress, "Loaded saved tactic data.", 1)

            if loadResult.source == "objectModel" and not forceRebuild:
                self._progressUpdate(progress, "Tactic model already available.", 4)
                logger.info(f"existing tactic model retained for {tacticName}")
                self.statusBar().showMessage(
                    f"{tacticName} is already processed into the tactic model.",
                    8000,
                )
                if openDetail:
                    self.tacticShow(tacticName)
                return

            if forceRebuild:
                self._progressUpdate(
                    progress,
                    "Regenerating structured data from saved captures...",
                    2,
                )
                self._progressBusy(progress, "Reading screenshot evidence with OCR...")
                extraction = self._backgroundRun(
                    lambda: self.tacticScreenshotExtractor.tacticExtract(tacticName)
                )
                self._progressRestore(progress, "Screenshot extraction finished.", 3)
                logger.info(
                    f"regeneration extraction result: created={extraction.structuredCreated}, "
                    f"complete={extraction.complete}, "
                    f"captures={getattr(extraction, 'screenshotCount', 'unknown')}"
                )
                if not extraction.structuredCreated:
                    logger.info(f"regeneration stopped: {extraction.message}")
                    self.statusBar().showMessage(
                        f"Unable to regenerate {tacticName}: {extraction.message}",
                        12000,
                    )
                    if openDetail:
                        self.tacticShow(tacticName)
                    return

                # A failed regeneration remains useful screenshot-derived
                # evidence, but it must never replace the current saved model.
                if not extraction.complete:
                    logger.info("regeneration stopped by incomplete extraction integrity gate")
                    self.statusBar().showMessage(
                        f"Regeneration incomplete for {tacticName}; existing model retained.",
                        15000,
                    )
                    if openDetail:
                        self.tacticShow(tacticName)
                    return

                self._progressUpdate(
                    progress,
                    "Building tactic model from regenerated data...",
                    3,
                )
                loadResult = self.tacticModelLoader.tacticLoad(tacticName, preferStructured=True)
                self._progressUpdate(progress, "Built regenerated tactic model.", 4)
                if loadResult.tactic is None:
                    logger.info("regeneration stopped because model build returned no tactic")
                    self.statusBar().showMessage(
                        f"Regeneration finished for {tacticName}, but model build still failed.",
                        12000,
                    )
                    if openDetail:
                        self.tacticShow(tacticName)
                    return
                if not self._generatedModelValid(loadResult.tactic):
                    logger.info("regeneration stopped by generated-model integrity gate")
                    self.statusBar().showMessage(
                        f"Regeneration invalid for {tacticName}; existing model retained.",
                        15000,
                    )
                    if openDetail:
                        self.tacticShow(tacticName)
                    return

            if not forceRebuild:
                self._progressUpdate(
                    progress,
                    "Building tactic model from structured data...",
                    2,
                )

            if loadResult.tactic is None and not forceRebuild:
                self._progressUpdate(
                    progress,
                    "Extracting structured data from saved captures...",
                    3,
                )
                self._progressBusy(progress, "Reading screenshot evidence with OCR...")
                extraction = self._backgroundRun(
                    lambda: self.tacticScreenshotExtractor.tacticExtract(tacticName)
                )
                self._progressRestore(progress, "Screenshot extraction finished.", 4)
                logger.info(
                    f"processing extraction result: created={extraction.structuredCreated}, "
                    f"complete={extraction.complete}, "
                    f"captures={getattr(extraction, 'screenshotCount', 'unknown')}"
                )
                if not extraction.structuredCreated:
                    self.statusBar().showMessage(
                        f"Unable to process {tacticName}: {extraction.message}",
                        12000,
                    )
                    if openDetail:
                        self.tacticShow(tacticName)
                    return
                if not extraction.complete:
                    self.statusBar().showMessage(
                        f"Processing incomplete for {tacticName}; no model was saved.",
                        15000,
                    )
                    if openDetail:
                        self.tacticShow(tacticName)
                    return
                self._progressUpdate(progress, "Reloading structured model...", 4)
                loadResult = self.tacticModelLoader.tacticLoad(tacticName)
                if loadResult.tactic is None:
                    self.statusBar().showMessage(
                        f"Processing {tacticName} created structured data but model build still failed.",
                        12000,
                    )
                    if openDetail:
                        self.tacticShow(tacticName)
                    return
                if not self._generatedModelValid(loadResult.tactic):
                    self.statusBar().showMessage(
                        f"Processing invalid for {tacticName}; no model was saved.",
                        15000,
                    )
                    if openDetail:
                        self.tacticShow(tacticName)
                    return

            self._progressUpdate(progress, "Saving tactic model...", 5)
            TacticStore(self.database.engine).tacticSave(loadResult.tactic)
            self._progressUpdate(progress, "Tactic model saved.", 6)
            logger.done(f"tactic model saved for {tacticName}")

            self.statusBar().showMessage(
                (
                    f"Regenerated {tacticName} into the tactic model from saved screenshots."
                    if forceRebuild
                    else f"Processed {tacticName} into the tactic model."
                ),
                10000,
            )
            self.dataChanged.emit()
            if openDetail:
                self.tacticShow(tacticName)
        except Exception as exc:
            logger.exception(f"tactic processing failed for {tacticName}")
            self._errorShow("Tactic processing error", str(exc))
        finally:
            progress.close()

    def _tacticProgressCreate(self) -> QProgressDialog:
        """Create an opaque, readable progress dialog owned by the main window."""

        progress = QProgressDialog("Processing tactic model...", None, 0, 6, self)
        progress.setObjectName("tacticProgressDialog")
        progress.setWindowTitle("Process Tactic")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimumWidth(560)
        progress.setMinimumHeight(140)
        progress.resize(560, 140)
        progress.setStyleSheet(
            "QProgressDialog#tacticProgressDialog { background-color: #101f2e; "
            "color: #e8eef5; } "
            "QProgressDialog#tacticProgressDialog QLabel { background: transparent; "
            "color: #e8eef5; font-size: 14px; font-weight: 600; "
            "padding: 12px 10px; min-height: 34px; } "
            "QProgressDialog#tacticProgressDialog QProgressBar { "
            "background-color: #08131f; color: #e8eef5; border: 1px solid #30465a; "
            "border-radius: 7px; min-height: 24px; text-align: center; } "
            "QProgressDialog#tacticProgressDialog QProgressBar::chunk { "
            "background-color: #31b98f; border-radius: 6px; }"
        )
        return progress

    def _backgroundRun(self, action: Callable[[], ResultType]) -> ResultType:
        """Run blocking extraction while the Qt interface continues processing events."""

        logger.doing("running tactic extraction worker")
        with ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="tactic-extraction",
        ) as executor:
            future = executor.submit(action)
            loop = QEventLoop(self)
            completionPoll = QTimer(self)
            completionPoll.setInterval(50)
            completionPoll.timeout.connect(
                lambda: loop.quit() if future.done() else None
            )
            completionPoll.start()
            loop.exec()
            completionPoll.stop()
            result = future.result()
        logger.done("tactic extraction worker finished")
        return result

    @staticmethod
    def _progressBusy(progress: QProgressDialog, message: str) -> None:
        """Show animated indeterminate progress during variable-duration OCR work."""

        logger.info(f"tactic progress busy: {message}")
        progress.setLabelText(message)
        progress.setRange(0, 0)
        progress.repaint()
        QApplication.processEvents()

    @staticmethod
    def _progressRestore(
        progress: QProgressDialog,
        message: str,
        value: int,
    ) -> None:
        """Restore the six-stage progress range after indeterminate OCR work."""

        progress.setRange(0, 6)
        MainWindow._progressUpdate(progress, message, value)

    @staticmethod
    def _progressUpdate(
        progress: QProgressDialog,
        message: str,
        value: int,
    ) -> None:
        """Paint one progress step before a potentially blocking operation."""

        logger.info(f"tactic progress {value}/{progress.maximum()}: {message}")
        progress.setLabelText(message)
        progress.setValue(value)
        progress.adjustSize()
        if progress.width() < 560 or progress.height() < 140:
            progress.resize(max(560, progress.width()), max(140, progress.height()))
        progress.repaint()
        QApplication.processEvents()

    @staticmethod
    def _generatedModelValid(tactic: ModelTactic) -> bool:
        """Return whether a generated tactic is safe to persist as the usable model."""

        for formation in (tactic.inPossession, tactic.outOfPossession):
            if len(formation.positions) != 11:
                return False
            for position in formation.positions:
                if (
                    not position.slotId
                    or not position.duty
                    or position.x is None
                    or position.y is None
                    or position.confidence is None
                    or position.sourceImportSessionId is None
                    or position.validationState == "unresolved"
                ):
                    return False
        return True

    def _tacticImportRun(self, tacticName: str | None = None) -> None:
        """Run tactic import flow, optionally anchored to a known tactic name."""

        if tacticName is None:
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
            outstanding = [item for item in tacticRequirements if item.screenType not in captured]
            if remaining:
                nextMessage = f" Next: {remaining[0].title}."
            elif outstanding:
                nextMessage = " Still missing: " + ", ".join(item.title for item in outstanding)
                nextMessage += "."
            else:
                nextMessage = " Tactic import is complete."
            self.statusBar().showMessage(
                f"Saved {requirement.title} for {tacticName} "
                f"as import {session.id}.{nextMessage}",
                10000,
            )
            self.dataChanged.emit()

        # After a full tactic capture set is available, immediately process
        # it into structured/object-model rows from the saved screenshots.
        if tacticName and {
            ScreenType.TACTIC_FORMATION,
            ScreenType.TACTIC_IN_POSSESSION,
            ScreenType.TACTIC_OUT_OF_POSSESSION,
        }.issubset(captured):
            self.tacticProcess(tacticName, openDetail=False)

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

    def tacticApplyToSquad(self, tacticName: str | None = None) -> None:
        """Pair an independently stored squad with a completed tactic."""

        squadName = self._squadSelect(existingOnly=True)
        if squadName is None:
            return
        if tacticName is None:
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

    def roleProfileImport(self) -> None:
        """Capture, review, and confirm one Football Manager role profile."""

        if self.roleKnowledgeService is None or self.tacticVocabulary is None:
            self._errorShow("Role profiles unavailable", "Role-profile knowledge is not configured")
            return
        roleEntries = sorted(
            self.tacticVocabulary.roles.values(),
            key=lambda role: (
                self.roleKnowledgeService.definitionExists(role.code),
                WelcomeService.roleSortKey(role),
            ),
        )
        roleLabels = {"New role…": None}
        for role in roleEntries:
            abbreviation = role.abbreviations[0] if role.abbreviations else role.code
            roleLabels[f"{role.displayName} ({abbreviation})"] = role
        selected, accepted = QInputDialog.getItem(
            self,
            "Expected role",
            "Choose the role shown in Football Manager:",
            list(roleLabels),
            0,
            False,
        )
        if not accepted:
            return
        role = roleLabels[selected]
        expectedPosition = ""
        if role is None:
            # New roles are not anchored to a canonical role yet, so ask for
            # the expected tactical position to guide review defaults.
            positions = sorted(
                set(self.tacticVocabulary.positions.values()),
                key=WelcomeService.positionSortKey,
            )
            expectedPosition, accepted = QInputDialog.getItem(
                self,
                "Expected position",
                "Choose the position shown in Football Manager:",
                positions,
                0,
                False,
            )
            if not accepted:
                return
        replaceExisting = (
            self.roleKnowledgeService.definitionExists(role.code) if role is not None else False
        )
        result = self._screenshotAcquire(ScreenType.ROLE_PROFILE, "Import Role")
        if result is None or result.roleProfile is None:
            return
        normalizedPosition = self.tacticVocabulary.positionNormalize(result.roleProfile.position)
        if role is not None and not normalizedPosition.resolved:
            self._errorShow(
                "Role unavailable",
                "The imported role profile does not contain a recognized position.",
            )
            return
        expectedRole = role.code if role is not None else ""
        storageName = role.code if role is not None else "newRole"
        try:
            screenshotPath = self._screenshotPersist(result, "role", storageName)
        except ScreenshotStoreError as exc:
            self._errorShow("Screenshot storage error", str(exc))
            return
        evidence = replace(result.roleProfile, sourceImport=str(screenshotPath))
        dialog = RoleProfileReviewDialog(
            evidence,
            expectedPosition or normalizedPosition.value,
            expectedRole,
            self.roleKnowledgeService,
            self,
            replaceExisting=replaceExisting,
            attributeDefinitions=self.attributes,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.screenshotStore.capturesRemove([screenshotPath])
            return
        self.statusBar().showMessage(
            f"Saved confirmed role definition: {dialog.savedPath}",
            10000,
        )
        self.dataChanged.emit()

    def rolesShow(self) -> None:
        """Show the refreshed captured-roles panel on the welcome workspace."""

        self.welcomeView.refresh()
        self.contentStack.setCurrentWidget(self.welcomeView)

    def tacticShow(self, tacticName: str) -> None:
        """Open one tactic using the persisted football object model when available."""

        try:
            detailRecord = self.database.tacticDetailRecord(tacticName)
        except DatabaseError as exc:
            self._errorShow("Database error", str(exc))
            return
        loadResult = self.tacticModelLoader.tacticLoad(tacticName)
        if loadResult.tactic is None:
            reason = "; ".join(issue.message for issue in loadResult.issues) or "No model data"
            detailModel = tacticDetailIncompleteModelBuild(
                tacticName,
                reason=reason,
                assignedSquads=detailRecord.assignedSquads if detailRecord is not None else (),
                updatedAt=detailRecord.updatedAt if detailRecord is not None else None,
            )
            self.tacticDetailView.tacticShow(
                tacticName,
                detailModel,
                sourceLabel="Incomplete Data",
                validation=loadResult,
            )
            self.contentStack.setCurrentWidget(self.tacticDetailView)
            self.statusBar().showMessage(
                f"Opened {tacticName} with incomplete tactic data; import/confirm tactic screenshots to complete the model.",
                12000,
            )
            return
        detailModel = tacticDetailModelBuild(
            loadResult.tactic,
            source=loadResult.source,
            complete=loadResult.complete,
            confirmed=loadResult.confirmed,
            metadata=loadResult.metadata,
            phaseSlots=loadResult.phaseSlots,
            assignedSquads=detailRecord.assignedSquads if detailRecord is not None else (),
            updatedAt=detailRecord.updatedAt if detailRecord is not None else None,
        )
        sourceLabel = "Saved Tactic Model" if loadResult.source == "objectModel" else "Built Model"
        self.tacticDetailView.tacticShow(
            loadResult.tactic.name,
            detailModel,
            sourceLabel=sourceLabel,
            validation=loadResult,
        )
        self.contentStack.setCurrentWidget(self.tacticDetailView)

    def _tacticDetailBack(self) -> None:
        """Return from tactic detail to the refreshed workspace."""

        self.welcomeView.refresh()
        self.contentStack.setCurrentWidget(self.welcomeView)

    def roleShow(self, roleCode: str) -> None:
        """Load one captured role definition into the review dialog for editing."""

        if self.roleKnowledgeService is None or self.tacticVocabulary is None:
            self._errorShow("Roles unavailable", "Role-profile knowledge is not configured")
            return
        role = self.tacticVocabulary.roles.get(roleCode)
        roleID = role.roleID if role is not None else self._roleIDParse(roleCode)
        content = (
            self.roleKnowledgeService.definitionLoad(roleCode)
            if role is not None
            else (
                self.roleKnowledgeService.definitionLoadByRoleID(roleID)
                if roleID is not None
                else None
            )
        )
        if content is None:
            self._errorShow("Role unavailable", "The captured role definition could not be loaded")
            return
        positions = self._stringsTuple(content.get("positions")) or (
            role.positions if role is not None else ()
        )
        if not positions:
            self._errorShow("Role unavailable", "The captured role definition has no positions")
            return
        phases = tuple(
            phase
            for phase, field in (
                (TacticalPhase.IN_POSSESSION, "inPossession"),
                (TacticalPhase.OUT_OF_POSSESSION, "outOfPossession"),
            )
            if content.get(field) is True
        )
        abbreviations = self._stringsTuple(content.get("abbreviations"))
        evidence = RoleProfileEvidence(
            position=positions[0],
            roleName=str(content.get("displayName") or role.displayName),
            phase=phases[0] if phases else None,
            abbreviation=abbreviations[0] if abbreviations else None,
            description=(
                str(content["description"]) if content.get("description") is not None else None
            ),
            behaviours=self._stringsTuple(content.get("behaviours")),
            keyAttributes=self._stringsTuple(content.get("keyAttributes")),
            playerInstructions=self._stringsTuple(content.get("playerInstructions")),
        )
        dialog = RoleProfileReviewDialog(
            evidence,
            positions[0],
            roleCode if role is not None else "",
            self.roleKnowledgeService,
            self,
            existingRoleID=roleID,
            replaceExisting=True,
            supportedPositions=positions,
            attributeWeights=self.roleKnowledgeService.weightsLoad(roleID or 0),
            attributeImportance=self.roleKnowledgeService.importanceLoad(roleID or 0),
            attributeDefinitions=self.attributes,
            phases=phases,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.profileDeleted:
            self.statusBar().showMessage("Deleted role definition", 10000)
        else:
            self.statusBar().showMessage(f"Updated role definition: {dialog.savedPath}", 10000)
        self.dataChanged.emit()

    @staticmethod
    def _roleIDParse(reference: str) -> int | None:
        if not reference.startswith("roleID:"):
            return None
        suffix = reference.removeprefix("roleID:").strip()
        return int(suffix) if suffix.isdigit() else None

    def managementShow(self, tabName: str, recordName: str | None = None) -> None:
        """Open or refresh the non-modal tactic and squad management window."""

        if self.managementWindow is None:
            self.managementWindow = ManagementWindow(
                self.database,
                self.screenshotStore,
                self,
                tacticApply=self.tacticApplyToSquad,
            )
            self.managementWindow.destroyed.connect(self._managementForget)
            self.managementWindow.dataChanged.connect(self.dataChanged.emit)
            self.dataChanged.connect(self.managementWindow.dataRefresh)
        else:
            self.managementWindow.dataRefresh()
        self.managementWindow.recordShow(tabName, recordName)
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
        sanity = self.validator.correctAll(
            players,
            context=f"confirmed squad={self.currentSquad}",
        )
        players, mergedDuplicates = self.validator.duplicatesMerge(
            list(sanity.players),
            context=f"confirmed squad={self.currentSquad}",
        )
        sanity = self.validator.correctAll(
            players,
            context=f"confirmed merged squad={self.currentSquad}",
        )
        players = list(sanity.players)
        if sanity.blockingIssues:
            lines = [
                f"Row {row + 1}, {issue.field}: {issue.message}"
                for row, issue in sanity.blockingIssues[:20]
            ]
            logger.warning(
                "sanity save blocked squad=%s issues=%d",
                self.currentSquad,
                len(sanity.blockingIssues),
            )
            QMessageBox.warning(
                self,
                "Correct player data before saving",
                "FMSAT found data that cannot be saved safely:\n\n" + "\n".join(lines),
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
            screenshotPaths = self._squadScreenshotsPersist(
                self.currentResult,
                self.currentSquad,
            )
        except ScreenshotStoreError as exc:
            self._errorShow("Screenshot storage error", str(exc))
            return
        try:
            session = self.database.squadImportBatchSave(
                [str(path) for path in screenshotPaths],
                players,
                self.currentSquad,
            )
        except DatabaseError as exc:
            self.screenshotStore.capturesRemove(screenshotPaths)
            self._errorShow("Database error", str(exc))
            return
        self.currentResult.source = str(screenshotPaths[0])
        self.saveAction.setEnabled(False)
        self.statusBar().showMessage(
            f"Saved {self.currentSquad}: import {session.id} with {len(players)} new player(s)"
            + (f"; merged {mergedDuplicates} duplicate row(s)" if mergedDuplicates else "")
            + (f"; skipped {skipped} existing or duplicate row(s)" if skipped else "")
            + (
                f"; missing data remains for {len(sanity.missingPlayers)} player(s)"
                if sanity.missingPlayers
                else ""
            ),
            8000,
        )
        self.dataChanged.emit()

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
        self.importRoleProfileAction = QAction("Import Role", self)
        self.importRoleProfileAction.triggered.connect(self.roleProfileImport)
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
        self.rolesAction = QAction("Roles", self)
        self.rolesAction.triggered.connect(self.rolesShow)
        self.settingsAction = QAction("Settings", self)
        self.settingsAction.triggered.connect(self.settingsShow)
        self.saveAction = QAction("Save Confirmed Data", self)
        self.saveAction.setShortcut("Ctrl+S")
        self.saveAction.setEnabled(False)
        self.saveAction.triggered.connect(self.reviewSave)
        self.exitAction = QAction("Exit", self)
        self.exitAction.triggered.connect(self.close)

    def _contentCreate(self) -> None:
        self.contentStack = QStackedWidget(self)
        self.welcomeView = WelcomeView(
            WelcomeService(
                self.database,
                self.tacticVocabulary,
                self.roleKnowledgeService,
            ),
            (
                self.importTacticAction,
                self.importSquadAction,
                self.importRoleProfileAction,
            ),
            self.tacticShow,
            self.tacticProcess,
            lambda name: self.managementShow("Squads", name),
            self.roleShow,
            self,
        )
        self.contentStack.addWidget(self.welcomeView)
        self.tacticDetailView = TacticDetailView(self)
        self.tacticDetailView.backRequested.connect(self._tacticDetailBack)
        self.tacticDetailView.assignmentRequested.connect(self.tacticApplyToSquad)
        self.tacticDetailView.importToModelRequested.connect(self.tacticModelImport)
        self.contentStack.addWidget(self.tacticDetailView)
        self.reviewWidget = QWidget(self)
        layout = QVBoxLayout(self.reviewWidget)
        self.instructions = QLabel(
            "Import three tactic screenshots, then capture one or more Squad Attributes "
            "screenshots in any player-page or attribute-view order. "
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
        self.table.itemChanged.connect(self._reviewItemChanged)
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
        self.contentStack.addWidget(self.reviewWidget)
        self.contentStack.setCurrentWidget(self.welcomeView)
        self.setCentralWidget(self.contentStack)

    def _errorShow(self, title: str, message: str) -> None:
        logger.warning("%s: %s", title, message)
        self.statusBar().showMessage(message, 10000)
        QMessageBox.critical(self, title, message)

    def _screenshotAcquire(
        self,
        expectedType: ScreenType,
        dialogTitle: str,
    ) -> ImportResult | None:
        """Collect a clipboard screenshot, prompting the user when none is available."""

        while True:
            clipboardImage = QApplication.clipboard().image()
            image: np.ndarray | None = None
            previewImage = clipboardImage
            source = "clipboard"
            if clipboardImage.isNull():
                if not self._screenshotReadyWait(
                    "Take screenshot",
                    f"Take the requested {dialogTitle.lower()} and leave it on the clipboard.",
                    allowBack=True,
                    backText="Cancel",
                ):
                    return None
                continue
            image = self._qImageConvert(clipboardImage)

            previewChoice = self._screenshotPreview(previewImage, dialogTitle)
            if previewChoice == "use":
                break
            if previewChoice == "cancel":
                return None

            if not self._screenshotReadyWait(
                "Take new screenshot",
                f"Take a new {dialogTitle.lower()} and leave it on the clipboard.",
                allowBack=True,
                backText="Cancel",
            ):
                return None

        self.statusBar().showMessage(f"Importing {expectedType.value} screenshot…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        importError: ImportError | OSError | None = None
        try:
            result = self.importService.imageImport(image, expectedType, source)
        except (ImportError, OSError) as exc:
            importError = exc
        finally:
            QApplication.restoreOverrideCursor()
        if importError is not None and "No player rows could be extracted" in str(importError):
            if not self._screenshotReadyWait(
                "Please retake screenshot",
                str(importError),
                allowBack=True,
                backText="Cancel",
            ):
                return None
            return self._screenshotAcquire(expectedType, dialogTitle)
        if importError is not None:
            self._errorShow("Import failed", str(importError))
            return None
        return result

    def _screenshotPreview(self, image: QImage, dialogTitle: str) -> str:
        """Ask the user to confirm the screenshot FMSAT is about to import."""

        preview = QPixmap.fromImage(image).scaled(
            480,
            270,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Confirm {dialogTitle}")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("FMSAT sees this screenshot:"))
        previewLabel = QLabel()
        previewLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        previewLabel.setPixmap(preview)
        layout.addWidget(previewLabel)
        information = QLabel("Continue only if this is the requested Football Manager screen.")
        information.setWordWrap(True)
        layout.addWidget(information)

        choice = "cancel"

        def choiceSet(value: str) -> None:
            nonlocal choice
            choice = value
            dialog.accept()

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancelButton = QPushButton("Cancel")
        cancelButton.clicked.connect(dialog.reject)
        buttons.addWidget(cancelButton)
        retakeButton = QPushButton("Take new screenshot")
        retakeButton.clicked.connect(lambda: choiceSet("retake"))
        buttons.addWidget(retakeButton)
        useButton = QPushButton("Use screenshot")
        useButton.clicked.connect(lambda: choiceSet("use"))
        useButton.setDefault(True)
        buttons.addWidget(useButton)
        layout.addLayout(buttons)

        dialog.exec()
        return choice

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

    def _squadScreenshotsPersist(
        self,
        result: ImportResult,
        squadName: str,
    ) -> list[Path]:
        """Persist every source screenshot collected for a squad import."""

        images = ([result.image] if result.image is not None else []) + result.additionalImages
        if not images:
            raise ScreenshotStoreError("A squad import requires at least one screenshot")
        paths: list[Path] = []
        try:
            for image in images:
                paths.append(
                    self.screenshotStore.captureSave(
                        image,
                        "squad",
                        squadName,
                        result.screenType.value,
                    )
                )
        except ScreenshotStoreError:
            self.screenshotStore.capturesRemove(paths)
            raise
        return paths

    def _menuCreate(self) -> None:
        fileMenu = self.menuBar().addMenu("&File")
        fileMenu.addAction(self.importTacticAction)
        fileMenu.addAction(self.importSquadAction)
        fileMenu.addAction(self.importRoleProfileAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.exitAction)
        viewMenu = self.menuBar().addMenu("&View")
        viewMenu.addAction(self.tacticsAction)
        viewMenu.addAction(self.squadsAction)
        viewMenu.addAction(self.rolesAction)
        viewMenu.addAction(self.playersAction)
        viewMenu.addAction(self.settingsAction)

    def _managementForget(self) -> None:
        self.dataChanged.emit()
        self.managementWindow = None

    def _qImageConvert(self, image: QImage) -> np.ndarray:
        converted = image.convertToFormat(QImage.Format.Format_RGB888)
        array = np.frombuffer(converted.bits(), dtype=np.uint8).reshape(
            converted.height(), converted.bytesPerLine()
        )
        rgb = array[:, : converted.width() * 3].reshape(converted.height(), converted.width(), 3)
        return rgb[:, :, ::-1].copy()

    def _resultShow(self, result: ImportResult) -> None:
        self.contentStack.setCurrentWidget(self.reviewWidget)
        sanity = self.validator.correctAll(
            result.players,
            context=f"review source={result.source}",
        )
        result.players = list(sanity.players)
        self.currentSanityReport = sanity
        self.currentResult = result
        collectedNames = {name for player in result.players for name in player.attributes.keys()}
        self.currentDisplayedAttributes = tuple(
            attribute for attribute in self.attributes if attribute.name in collectedNames
        )
        signalBlocker = QSignalBlocker(self.table)
        self.table.setColumnCount(len(self.baseColumns) + len(self.currentDisplayedAttributes) + 1)
        self.table.setHorizontalHeaderLabels(
            [
                *self.baseColumns,
                *(attribute.abbreviation for attribute in self.currentDisplayedAttributes),
                "Confidence",
            ]
        )
        self.table.setRowCount(len(result.players))
        self.table.setVerticalHeaderLabels(
            [str(self.currentSquadPlayerOffset + row + 1) for row in range(len(result.players))]
        )
        for row, player in enumerate(result.players):
            rowIssues = [issue for issueRow, issue in sanity.issues if issueRow == row]
            blockingIssues = [issue for issue in rowIssues if issue.blocking]
            values = [
                player.name,
                player.positions,
                player.ca,
                player.pa,
                *(
                    (
                        ""
                        if player.attributes.get(attribute.name) is None
                        else str(player.attributes[attribute.name])
                    )
                    for attribute in self.currentDisplayedAttributes
                ),
                f"{player.confidence:.1%}",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == len(values) - 1:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if blockingIssues:
                    item.setBackground(QColor("#ffc9c9"))
                elif rowIssues:
                    item.setBackground(QColor("#fff1b8"))
                if rowIssues:
                    item.setToolTip(
                        "\n".join(f"{issue.field}: {issue.message}" for issue in rowIssues)
                    )
                self.table.setItem(row, column, item)
        del signalBlocker
        self.saveAction.setEnabled(True)
        summary = []
        if sanity.blockingIssues:
            summary.append(f"{len(sanity.blockingIssues)} blocking issue(s)")
        if sanity.missingPlayers:
            summary.append(f"missing data for {len(sanity.missingPlayers)} player(s)")
        if sanity.corrections:
            summary.append(f"{len(sanity.corrections)} automatic correction(s)")
        self.statusBar().showMessage(
            f"Extracted {len(result.players)} player(s) for {self.currentSquad} — "
            + (", ".join(summary) if summary else "sanity checks passed")
        )

    def _reviewItemChanged(self, item: QTableWidgetItem) -> None:
        """Refresh review highlighting immediately after a manual cell edit."""

        if self.currentResult is None or item.row() >= self.table.rowCount():
            return
        if any(
            self.table.item(item.row(), column) is None
            for column in range(self.table.columnCount())
        ):
            return
        players = self._tablePlayersRead()
        if item.row() >= len(players):
            return
        issues = self.validator.validate(players[item.row()])
        blocking = any(issue.blocking for issue in issues)
        tooltip = "\n".join(f"{issue.field}: {issue.message}" for issue in issues)
        self.table.blockSignals(True)
        try:
            for column in range(self.table.columnCount()):
                cell = self.table.item(item.row(), column)
                if cell is None:
                    continue
                if blocking:
                    cell.setBackground(QColor("#ffc9c9"))
                elif issues:
                    cell.setBackground(QColor("#fff1b8"))
                else:
                    cell.setData(Qt.ItemDataRole.BackgroundRole, None)
                cell.setToolTip(tooltip)
        finally:
            self.table.blockSignals(False)

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
            choices = squads if existingOnly else [*squads, "Create new squad…"]
            selectedIndex = choices.index(self.currentSquad) if self.currentSquad in squads else 0
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

    @staticmethod
    def _stringsTuple(value: object) -> tuple[str, ...]:
        """Return non-empty strings from a stored YAML sequence."""

        if not isinstance(value, list):
            return ()
        return tuple(str(item) for item in value if str(item).strip())

    def _tablePlayersRead(self) -> list[ExtractedPlayer]:
        if self.currentResult is None:
            return []
        players: list[ExtractedPlayer] = []
        for row in range(self.table.rowCount()):
            original = self.currentResult.players[row]
            attributes: dict[str, int | None] = {}
            for offset, definition in enumerate(self.currentDisplayedAttributes, start=4):
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
        ):
            toolbar.addAction(action)
        self.addToolBar(toolbar)
