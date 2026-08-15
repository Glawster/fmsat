"""Editable squad assessment workspace for requirement 007."""

from __future__ import annotations

from importlib.resources import files

from fmsat.core.logUtils import getLogger
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QProgressDialog,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.squadDetailModel import SquadDetailModel
from fmsat.app.squadDetailTabOverrides import SquadAnalysisTab, SquadRolesTab
from fmsat.app.squadDetailTabs import SquadOverviewTab, SquadPlayersTab
from fmsat.core.config import AttributeDefinition
from fmsat.core.squadModel import SquadModel

logger = getLogger()


class SquadDetailView(QWidget):
    """Coordinate squad facts, editable players, roles, and generated analysis."""

    backRequested = Signal()
    modelSaveRequested = Signal(object)
    tacticSelected = Signal(str, str)

    def __init__(
        self,
        parent: QWidget | None = None,
        attributes: tuple[AttributeDefinition, ...] = (),
    ) -> None:
        super().__init__(parent)
        self.attributes = attributes
        self.model: SquadDetailModel | None = None
        self.squadName = ""
        self.regenerationProgress: QProgressDialog | None = None
        self.setObjectName("squadDetailView")
        self.setStyleSheet(files("fmsat.app").joinpath("fmsat.qss").read_text(encoding="utf-8"))
        self.rootLayout = QVBoxLayout(self)
        self.rootLayout.setContentsMargins(28, 20, 28, 24)
        self.rootLayout.setSpacing(16)

    def squadShow(self, squadName: str, model: SquadDetailModel) -> None:
        """Replace the current squad context and rebuild its bounded workspace."""

        self.squadName = squadName
        self.model = model
        self._contentRefresh()

    ## layout

    def _contentRefresh(self) -> None:
        self._layoutClear(self.rootLayout)
        if self.model is None:
            return
        self.rootLayout.addLayout(self._headerCreate())
        self.rootLayout.addLayout(self._factsCreate())
        self.rootLayout.addWidget(self._tabsCreate(), 1)
        footer = QHBoxLayout()
        footer.addStretch()
        if self.model.squad.regenerationRequired:
            self.regenerateButton = QPushButton("Regenerate Squad Model")
            self.regenerateButton.setToolTip(
                "Rebuild the squad model from the newer saved squad screenshots."
            )
            self.regenerateButton.clicked.connect(self._regenerateRequest)
            footer.addWidget(self.regenerateButton)
        else:
            self.regenerateButton = None
        self.saveButton = QPushButton("Save Squad Model")
        self.saveButton.setEnabled(False)
        self.saveButton.clicked.connect(self._saveRequest)
        footer.addWidget(self.saveButton)
        self.rootLayout.addLayout(footer)

    def _headerCreate(self) -> QHBoxLayout:
        assert self.model is not None
        header = QHBoxLayout()
        back = QPushButton("←  FMSAT Workspace")
        back.setObjectName("quietButton")
        back.clicked.connect(self.backRequested.emit)
        header.addWidget(back)
        heading = QVBoxLayout()
        eyebrow = QLabel("Squad Workspace  ·  Role-Level Assessment")
        eyebrow.setObjectName("eyebrow")
        heading.addWidget(eyebrow)
        title = QLabel(self.squadName)
        title.setObjectName("pageTitle")
        heading.addWidget(title)
        header.addLayout(heading, 1)
        self.tacticPicker = QComboBox()
        self.tacticPicker.setObjectName("squadTacticPicker")
        availableTactics = self._systemTactics()
        tacticAssigned = self.model.tacticName not in {
            "No tactic selected",
            "No tactic assigned",
        }
        if not tacticAssigned:
            self.tacticPicker.addItem("No tactic assigned")
        self.tacticPicker.addItems(availableTactics)
        if tacticAssigned:
            selected = self.tacticPicker.findText(self.model.tacticName)
            if selected < 0:
                self.tacticPicker.addItem(self.model.tacticName)
                selected = self.tacticPicker.findText(self.model.tacticName)
            self.tacticPicker.setCurrentIndex(selected)
        elif availableTactics:
            self.tacticPicker.setCurrentIndex(0)
        else:
            self.tacticPicker.setEnabled(False)
        self.tacticPicker.currentTextChanged.connect(self._tacticChange)
        header.addWidget(self.tacticPicker)
        return header

    def _factsCreate(self) -> QHBoxLayout:
        assert self.model is not None
        covered = sum(not role.coverage.startswith("Uncovered") for role in self.model.roles)
        facts = QHBoxLayout()
        tacticName = (
            "No tactic assigned"
            if self.model.tacticName in {"No tactic selected", "No tactic assigned"}
            else self.model.tacticName
        )
        for label, value in (
            ("PLAYERS", str(len(self.model.squad.players))),
            ("TACTIC", tacticName),
            ("UNIQUE TACTIC ROLES", str(len(self.model.roles))),
            ("COVERED UNIQUE ROLES", f"{covered} of {len(self.model.roles)}"),
            ("STATUS", self.model.sourceStatus),
        ):
            facts.addWidget(self._factCardCreate(label, value), 1)
        return facts

    def _tabsCreate(self) -> QTabWidget:
        assert self.model is not None
        tabs = QTabWidget()
        tabs.setObjectName("squadTabs")
        tabs.addTab(SquadOverviewTab(self.model), "Overview")
        self.playersTab = SquadPlayersTab(self.model.squad, self.attributes)
        self.playersTab.changed.connect(lambda: self.saveButton.setEnabled(True))
        tabs.addTab(self.playersTab, "Players")
        tabs.addTab(SquadRolesTab(self.model.roles, self.attributes), "Roles")
        tabs.addTab(SquadAnalysisTab(self.model, self.attributes), "Analysis")
        return tabs

    ## actions

    def _saveRequest(self) -> None:
        model: SquadModel = self.playersTab.modelBuild()
        self.modelSaveRequested.emit(model)

    def _regenerateRequest(self) -> None:
        """Regenerate from saved evidence while keeping the UI visibly responsive."""

        if self.model is None or not self.model.squad.regenerationRequired:
            return
        if self.regenerateButton is not None:
            self.regenerateButton.setEnabled(False)

        logger.doing(f"requesting squad model regeneration for {self.squadName}")
        progress = self._regenerationProgressCreate()
        self.regenerationProgress = progress
        progress.show()
        QApplication.processEvents()
        try:
            logger.info("squad regeneration UI handing model to persistence service")
            self.modelSaveRequested.emit(self.model.squad)
            logger.done(f"squad regeneration UI completed for {self.squadName}")
        finally:
            progress.close()
            if self.regenerateButton is not None:
                self.regenerateButton.setEnabled(True)

    def _regenerationProgressCreate(self) -> QProgressDialog:
        """Create a visible indeterminate progress dialog for squad regeneration."""

        progress = QProgressDialog(
            "Regenerating squad model from saved screenshot evidence…",
            None,
            0,
            0,
            self,
        )
        progress.setObjectName("squadRegenerationProgressDialog")
        progress.setWindowTitle("Regenerate Squad Model")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimumWidth(560)
        progress.setMinimumHeight(140)
        progress.resize(560, 140)
        progress.setStyleSheet(
            "QProgressDialog#squadRegenerationProgressDialog { background-color: #101f2e; "
            "color: #e8eef5; } "
            "QProgressDialog#squadRegenerationProgressDialog QLabel { background: transparent; "
            "color: #e8eef5; font-size: 14px; font-weight: 600; "
            "padding: 12px 10px; min-height: 34px; } "
            "QProgressDialog#squadRegenerationProgressDialog QProgressBar { "
            "background-color: #08131f; color: #e8eef5; border: 1px solid #30465a; "
            "border-radius: 7px; min-height: 24px; text-align: center; } "
            "QProgressDialog#squadRegenerationProgressDialog QProgressBar::chunk { "
            "background-color: #31b98f; border-radius: 6px; }"
        )
        return progress

    def _tacticChange(self, tacticName: str) -> None:
        if self.model is None or tacticName in {"", "No tactic assigned"}:
            return
        if tacticName == self.model.tacticName:
            return
        database = getattr(self.window(), "database", None)
        if database is not None:
            try:
                database.tacticApplyToSquad(self.squadName, tacticName)
                logger.action(
                    "squad tactic selected squad=%r tactic=%r",
                    self.squadName,
                    tacticName,
                )
            except Exception as exc:  # UI boundary: keep database failures visible in logs.
                logger.exception(
                    "unable to assign tactic from squad workspace squad=%r tactic=%r",
                    self.squadName,
                    tacticName,
                )
                statusBar = getattr(self.window(), "statusBar", None)
                if callable(statusBar):
                    statusBar().showMessage(str(exc), 10000)
                return
        self.tacticSelected.emit(self.squadName, tacticName)

    def _systemTactics(self) -> tuple[str, ...]:
        """Return every stored tactic while retaining model-provided fallbacks."""

        assert self.model is not None
        names = set(self.model.availableTactics)
        database = getattr(self.window(), "database", None)
        if database is not None:
            try:
                names.update(database.tacticsList())
            except Exception:
                logger.exception("unable to list system tactics for squad workspace")
        return tuple(sorted((name for name in names if name.strip()), key=str.casefold))

    ## utilities

    @staticmethod
    def _factCardCreate(label: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("factCard")
        layout = QVBoxLayout(card)
        key = QLabel(label)
        key.setObjectName("factKey")
        layout.addWidget(key)
        fact = QLabel(value)
        fact.setObjectName("factValue")
        fact.setWordWrap(True)
        layout.addWidget(fact)
        return card

    def _layoutClear(self, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
            if item.layout() is not None:
                self._layoutClear(item.layout())
