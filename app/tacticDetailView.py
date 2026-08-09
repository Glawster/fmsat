"""Tactic-detail workspace orchestration for requirement 009."""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.tacticDetailModel import DisplaySlot, TacticDetailModel
from fmsat.app.tacticDetailPrototype import tacticDetailPrototype
from fmsat.app.tacticDetailTabs import AnalysisTab, InstructionsTab, OverviewTab, ShapeTab
from fmsat.app.tacticPitchWidget import PitchWidget

__all__ = ["DisplaySlot", "PitchWidget", "TacticDetailView"]


class TacticDetailView(QWidget):
    """Coordinate the header, facts, and tabs of the tactic workspace."""

    backRequested = Signal()
    assignmentRequested = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        model: TacticDetailModel | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model or tacticDetailPrototype()
        self.tacticName = ""
        self.setObjectName("tacticDetailView")
        self.setStyleSheet(self._styleLoad())
        self._layoutCreate()

    def tacticShow(self, tacticName: str) -> None:
        """Refresh the workspace for the selected stored tactic identity."""

        self.tacticName = tacticName
        self.titleLabel.setText(tacticName)
        self.assignmentButton.setText("Assign squad")

    ## layout

    def _factsCreate(self) -> QHBoxLayout:
        facts = QHBoxLayout()
        facts.setSpacing(10)
        for label, value in (
            ("FORMATION", self.model.formation),
            ("MENTALITY", self.model.mentality),
            ("STATUS", self.model.status),
            ("ASSIGNED SQUADS", self.model.assignedSquads),
            ("UPDATED", self.model.updated),
        ):
            facts.addWidget(self._factCardCreate(label, value), 1)
        return facts

    def _headerCreate(self) -> QHBoxLayout:
        header = QHBoxLayout()
        back = QPushButton("←  All tactics")
        back.setObjectName("quietButton")
        back.clicked.connect(self.backRequested.emit)
        header.addWidget(back)
        heading = QVBoxLayout()
        eyebrow = QLabel("Tactic Workspace  ·  Prototype Data")
        eyebrow.setObjectName("eyebrow")
        heading.addWidget(eyebrow)
        self.titleLabel = QLabel("Tactic")
        self.titleLabel.setObjectName("pageTitle")
        heading.addWidget(self.titleLabel)
        header.addLayout(heading, 1)
        revisions = QComboBox()
        revisions.setObjectName("revisionPicker")
        revisions.addItems(self.model.revisions)
        header.addWidget(revisions)
        compare = QPushButton("Compare")
        compare.setObjectName("secondaryButton")
        header.addWidget(compare)
        self.assignmentButton = QPushButton("Assign Squad")
        self.assignmentButton.clicked.connect(
            lambda: self.assignmentRequested.emit(self.tacticName)
        )
        header.addWidget(self.assignmentButton)
        return header

    def _layoutCreate(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 24)
        root.setSpacing(16)
        root.addLayout(self._headerCreate())
        root.addLayout(self._factsCreate())
        root.addWidget(self._tabsCreate(), 1)

    def _tabsCreate(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setObjectName("tacticTabs")
        tabs.addTab(OverviewTab(self.model), "Overview")
        tabs.addTab(ShapeTab(self.model), "Team Shape")
        tabs.addTab(InstructionsTab(self.model), "Team Instructions")
        tabs.addTab(AnalysisTab(), "Analysis")
        return tabs

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

    @staticmethod
    def _styleLoad() -> str:
        return files("fmsat.app").joinpath("tacticDetail.qss").read_text(encoding="utf-8")
