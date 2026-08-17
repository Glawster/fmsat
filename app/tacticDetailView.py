"""Tactic-detail workspace orchestration for requirement 009."""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.tacticDetailModel import DisplaySlot, TacticDetailModel
from fmsat.app.tacticDetailPrototype import tacticDetailPrototype
from fmsat.app.tacticDetailTabs import AnalysisTab, InstructionsTab, OverviewTab, ShapeTab
from fmsat.app.tacticPitchWidget import PitchWidget
from fmsat.app.tacticValidationWidget import BuildResult
from fmsat.database.tacticNaming import TacticRenameError, tacticRename

__all__ = ["DisplaySlot", "PitchWidget", "TacticDetailView"]


class TacticDetailView(QWidget):
    """Coordinate the header, facts, and tabs of the tactic workspace."""

    backRequested = Signal()
    assignmentRequested = Signal(str)
    importToModelRequested = Signal(str)
    modelEditRequested = Signal(str)
    renameRequested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None, *, model: TacticDetailModel | None = None, validation: BuildResult | None = None) -> None:
        super().__init__(parent)
        self.model = model or tacticDetailPrototype()
        self.validation = validation
        self.sourceLabel = "Prototype Data"
        self.tacticName = ""
        self.setObjectName("tacticDetailView")
        self.setStyleSheet(self._styleLoad())
        self.rootLayout = QVBoxLayout(self)
        self.rootLayout.setContentsMargins(28, 20, 28, 24)
        self.rootLayout.setSpacing(16)
        self._contentRefresh()

    def tacticShow(self, tacticName: str, model: TacticDetailModel | None = None, *, sourceLabel: str | None = None, validation: BuildResult | None = None) -> None:
        """Refresh the workspace for the selected stored tactic identity."""
        if model is not None:
            self.model = model
        if sourceLabel is not None:
            self.sourceLabel = sourceLabel
        self.validation = validation
        self.tacticName = tacticName
        self._contentRefresh()

    ## layout

    def _factsCreate(self) -> QHBoxLayout:
        facts = QHBoxLayout()
        facts.setSpacing(10)
        for label, value in (("FORMATION", self.model.formation), ("MENTALITY", self.model.mentality), ("STATUS", self.model.status), ("ASSIGNED SQUADS", self.model.assignedSquads), ("UPDATED", self.model.updated)):
            facts.addWidget(self._factCardCreate(label, value), 1)
        return facts

    def _headerCreate(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(18)
        back = QPushButton("←  FMSAT Workspace")
        back.setObjectName("quietButton")
        back.clicked.connect(self.backRequested.emit)
        header.addWidget(back, 0, Qt.AlignmentFlag.AlignVCenter)

        heading = QVBoxLayout()
        heading.setSpacing(2)
        workspace = QLabel(f"Tactic Workspace  ·  {self.sourceLabel}")
        workspace.setObjectName("workspaceHeading")
        heading.addWidget(workspace)
        titleRow = QHBoxLayout()
        titleRow.setSpacing(12)
        self.titleLabel = QLabel(self.tacticName or "Tactic")
        self.titleLabel.setObjectName("pageTitle")
        titleRow.addWidget(self.titleLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        self.renameButton = QPushButton("Rename")
        self.renameButton.setObjectName("quietButton")
        self.renameButton.clicked.connect(self._renameBegin)
        titleRow.addWidget(self.renameButton, 0, Qt.AlignmentFlag.AlignVCenter)
        titleRow.addStretch()
        heading.addLayout(titleRow)
        header.addLayout(heading, 1)

        if self.model.revisions:
            revisions = QComboBox()
            revisions.setObjectName("revisionPicker")
            revisions.addItems(self.model.revisions)
            header.addWidget(revisions, 0, Qt.AlignmentFlag.AlignVCenter)
        compare = QPushButton("Compare")
        compare.setObjectName("secondaryButton")
        header.addWidget(compare, 0, Qt.AlignmentFlag.AlignVCenter)
        self.assignmentButton = QPushButton("Assign Squad")
        self.assignmentButton.clicked.connect(lambda: self.assignmentRequested.emit(self.tacticName))
        header.addWidget(self.assignmentButton, 0, Qt.AlignmentFlag.AlignVCenter)
        return header

    def _renameBegin(self) -> None:
        """Rename the persisted tactic identity without regenerating evidence."""
        oldName = self.tacticName
        newName, accepted = QInputDialog.getText(self, "Rename tactic", "Tactic name:", text=oldName)
        if not accepted or newName.strip() == oldName:
            return
        owner = self.window()
        database = getattr(owner, "database", None)
        if database is None or not hasattr(database, "engine"):
            self.renameRequested.emit(oldName, newName.strip())
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
        """Create bottom-row actions for tactic maintenance workflows."""
        footer = QHBoxLayout()
        footer.addStretch()
        editButton = QPushButton("Edit Model")
        editButton.setObjectName("secondaryButton")
        editButton.clicked.connect(lambda: self.modelEditRequested.emit(self.tacticName))
        footer.addWidget(editButton)
        self.importToModelButton = QPushButton("Regenerate Model")
        self.importToModelButton.clicked.connect(lambda: self.importToModelRequested.emit(self.tacticName))
        footer.addWidget(self.importToModelButton)
        return footer

    def _tabsCreate(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setObjectName("tacticTabs")
        self.overviewTab = OverviewTab(self.model, self.validation)
        tabs.addTab(self.overviewTab, "Overview")
        tabs.addTab(ShapeTab(self.model), "Shape")
        tabs.addTab(InstructionsTab(self.model), "Instructions")
        tabs.addTab(AnalysisTab(), "Analysis")
        return tabs

    ## utilities

    @staticmethod
    def _styleLoad() -> str:
        return files("fmsat.app").joinpath("fmsat.qss").read_text(encoding="utf-8")

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
