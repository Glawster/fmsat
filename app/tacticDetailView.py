"""Tactic-detail workspace orchestration for requirement 009."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLayout,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.adminWidgets import AdminTextEditDialog
from fmsat.app.tacticAnalysisWorkspace import AnalysisTab
from fmsat.app.tacticDetailModel import DisplaySlot, TacticDetailModel
from fmsat.app.tacticDetailPrototype import tacticDetailPrototype
from fmsat.app.tacticDetailTabs import InstructionsTab, OverviewTab, ShapeTab
from fmsat.core.tacticAnalysis import TacticAnalysis
from fmsat.app.tacticPitchWidget import PitchWidget
from fmsat.app.tacticValidationWidget import BuildResult
from fmsat.app.styles import styleSheetLoad
from fmsat.app.workspaceWidgets import FactCard, WorkspaceHeader
from fmsat.database.tacticNaming import TacticRenameError, tacticRename

__all__ = ["DisplaySlot", "PitchWidget", "TacticDetailView"]


class TacticDetailView(QWidget):
    """Coordinate the header, facts, and tabs of the tactic workspace."""

    backRequested = Signal()
    assignmentRequested = Signal(str)
    importToModelRequested = Signal(str)
    modelEditRequested = Signal(str)
    renameRequested = Signal(str, str)
    squadRequested = Signal(str)
    reanalyseRequested = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        model: TacticDetailModel | None = None,
        validation: BuildResult | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model or tacticDetailPrototype()
        self.validation = validation
        self.analysis: TacticAnalysis | None = None
        self.sourceLabel = "Prototype Data"
        self.tacticName = ""
        self.selectedTabName = "Overview"
        self.setObjectName("tacticDetailView")
        self.setStyleSheet(self._styleLoad())
        self.rootLayout = QVBoxLayout(self)
        self.rootLayout.setContentsMargins(28, 20, 28, 24)
        self.rootLayout.setSpacing(16)
        self._contentRefresh()

    def tacticShow(
        self,
        tacticName: str,
        model: TacticDetailModel | None = None,
        *,
        sourceLabel: str | None = None,
        validation: BuildResult | None = None,
        analysis: TacticAnalysis | None = None,
    ) -> None:
        """Refresh the workspace for the selected stored tactic identity."""

        if model is not None:
            self.model = model
        if sourceLabel is not None:
            self.sourceLabel = sourceLabel
        self.validation = validation
        self.analysis = analysis
        self.tacticName = tacticName
        self._contentRefresh()

    ## layout

    def _factsCreate(self) -> QHBoxLayout:
        """Create the shared workspace fact-card row."""

        facts = QHBoxLayout()
        facts.setSpacing(10)
        for label, value in (
            ("FORMATION", self.model.formation),
            ("MENTALITY", self.model.mentality),
            ("STATUS", self.model.status),
            ("ASSIGNED SQUADS", self.model.assignedSquads),
            ("UPDATED", self.model.updated),
        ):
            card = FactCard(label, value, self)
            if label == "ASSIGNED SQUADS" and self.model.assignedSquadNames:
                card.interactionEnable("Open assigned squad")
                card.activated.connect(lambda card=card: self._assignedSquadsOpen(card))
                self.assignedSquadsCard = card
            facts.addWidget(card, 1)
        return facts

    def _assignedSquadsOpen(self, card: FactCard) -> None:
        """Open the sole assigned squad or offer a menu when several are assigned."""

        squads = self.model.assignedSquadNames
        if len(squads) == 1:
            self.squadRequested.emit(squads[0])
            return
        menu = QMenu(card)
        menu.setObjectName("assignedSquadsMenu")
        for squadName in squads:
            action = menu.addAction(squadName)
            action.triggered.connect(
                lambda checked=False, name=squadName: self.squadRequested.emit(name)
            )
        self.assignedSquadsMenu = menu
        menu.popup(card.mapToGlobal(card.rect().bottomLeft()))

    def _headerCreate(self) -> QHBoxLayout:
        """Create the tactic header using the shared workspace header component."""

        self.renameButton = QPushButton("Rename")
        self.renameButton.setObjectName("quietButton")
        self.renameButton.clicked.connect(self._renameBegin)

        trailingActions: list[QWidget] = []
        if self.model.revisions:
            revisions = QComboBox()
            revisions.setObjectName("revisionPicker")
            revisions.addItems(self.model.revisions)
            trailingActions.append(revisions)

        compare = QPushButton("Compare")
        compare.setObjectName("secondaryButton")
        trailingActions.append(compare)

        self.assignmentButton = QPushButton("Assign Squad")
        self.assignmentButton.clicked.connect(
            lambda: self.assignmentRequested.emit(self.tacticName)
        )
        trailingActions.append(self.assignmentButton)

        header = WorkspaceHeader(
            workspace="Tactic",
            context=self.sourceLabel,
            title=self.tacticName or "Tactic",
            backRequested=self.backRequested.emit,
            titleActions=(self.renameButton,),
            trailingActions=trailingActions,
        )
        self.titleLabel = header.titleLabel
        return header.layout

    def _renameBegin(self) -> None:
        """Rename the persisted tactic identity without regenerating evidence."""

        oldName = self.tacticName
        dialog = AdminTextEditDialog(
            title="Rename tactic",
            label="Tactic name:",
            value=oldName,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        newName = dialog.value()
        if not newName or newName == oldName:
            return

        owner = self.window()
        database = getattr(owner, "database", None)
        if database is None or not hasattr(database, "engine"):
            self.renameRequested.emit(oldName, newName)
            return
        try:
            savedName = tacticRename(database.engine, oldName, newName)
        except TacticRenameError as exc:
            QMessageBox.warning(self, "Cannot rename tactic", str(exc))
            return
        self.tacticName = savedName
        self.titleLabel.setText(savedName)
        self.renameRequested.emit(oldName, savedName)
        dataChanged = getattr(owner, "dataChanged", None)
        if dataChanged is not None and hasattr(dataChanged, "emit"):
            dataChanged.emit()

    def _contentRefresh(self) -> None:
        """Rebuild all top-level sections after the active model changes."""

        self._layoutClear(self.rootLayout)
        self.rootLayout.addLayout(self._headerCreate())
        self.rootLayout.addLayout(self._factsCreate())
        self.rootLayout.addWidget(self._tabsCreate(), 1)
        self.rootLayout.addLayout(self._footerCreate())

    def _footerCreate(self) -> QHBoxLayout:
        """Create one aligned row of equal-width tactic maintenance actions."""

        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addStretch()
        self.editModelButton = QPushButton("Edit Model")
        self.editModelButton.clicked.connect(lambda: self.modelEditRequested.emit(self.tacticName))
        self.importToModelButton = QPushButton("Regenerate Model")
        self.importToModelButton.clicked.connect(
            lambda: self.importToModelRequested.emit(self.tacticName)
        )
        self.reanalyseButton = QPushButton("Reanalyse Tactic")
        self.reanalyseButton.setObjectName("reanalyseTacticButton")
        self.reanalyseButton.setToolTip(
            "Recalculate tactic demand from the saved football object model using the "
            "current role-assessment policy. Does not regenerate screenshots."
        )
        self.reanalyseButton.setEnabled(self.analysis is not None)
        self.reanalyseButton.clicked.connect(self.reanalyseRequested.emit)
        buttons = (self.editModelButton, self.importToModelButton, self.reanalyseButton)
        # sizeHint() is taken before QSS padding applies, so a raw fixed width
        # clips labels such as "Regenerate Model". Measure the text, then add
        # the workspace button padding plus a little extra room.
        self.ensurePolished()
        textWidth = max(button.fontMetrics().horizontalAdvance(button.text()) for button in buttons)
        width = textWidth + 56
        for button in buttons:
            button.setObjectName(button.objectName() or "workspaceActionButton")
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            button.setMinimumWidth(width)
            footer.addWidget(button)
        return footer

    def _tabsCreate(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setObjectName("tacticTabs")
        self.overviewTab = OverviewTab(self.model, self.validation)
        tabs.addTab(self.overviewTab, "Overview")
        tabs.addTab(ShapeTab(self.model), "Shape")
        tabs.addTab(InstructionsTab(self.model), "Instructions")
        self.analysisTab = AnalysisTab(self.analysis)
        tabs.addTab(self.analysisTab, "Analysis")
        self.tabs = tabs
        targetIndex = next(
            (index for index in range(tabs.count()) if tabs.tabText(index) == self.selectedTabName),
            0,
        )
        tabs.setCurrentIndex(targetIndex)
        tabs.currentChanged.connect(
            lambda index: setattr(self, "selectedTabName", tabs.tabText(index))
        )
        return tabs

    ## utilities

    @staticmethod
    def _styleLoad() -> str:
        return styleSheetLoad()

    def _layoutClear(self, layout: QLayout) -> None:
        """Delete all child widgets/layouts from one Qt layout container."""

        while layout.count():
            item = layout.takeAt(0)
            childWidget = item.widget()
            childLayout = item.layout()
            if childWidget is not None:
                childWidget.deleteLater()
            elif childLayout is not None:
                self._layoutClear(childLayout)
