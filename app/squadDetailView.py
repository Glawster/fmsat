"""Editable squad assessment workspace for requirement 007."""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.squadDetailModel import SquadDetailModel
from fmsat.app.squadDetailTabs import (
    SquadAnalysisTab,
    SquadOverviewTab,
    SquadPlayersTab,
    SquadRolesTab,
)
from fmsat.core.squadModel import SquadModel


class SquadDetailView(QWidget):
    """Coordinate squad facts, editable players, roles, and generated analysis."""

    backRequested = Signal()
    modelSaveRequested = Signal(object)
    tacticSelected = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model: SquadDetailModel | None = None
        self.squadName = ""
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
        if self.model.availableTactics:
            self.tacticPicker.addItems(self.model.availableTactics)
            selected = self.tacticPicker.findText(self.model.tacticName)
            self.tacticPicker.setCurrentIndex(max(0, selected))
        else:
            self.tacticPicker.addItem("No tactic assigned")
            self.tacticPicker.setEnabled(False)
        self.tacticPicker.currentTextChanged.connect(self._tacticChange)
        header.addWidget(self.tacticPicker)
        return header

    def _factsCreate(self) -> QHBoxLayout:
        assert self.model is not None
        covered = sum(not role.coverage.startswith("Uncovered") for role in self.model.roles)
        facts = QHBoxLayout()
        for label, value in (
            ("PLAYERS", str(len(self.model.squad.players))),
            ("TACTIC", self.model.tacticName),
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
        self.playersTab = SquadPlayersTab(self.model.squad)
        self.playersTab.changed.connect(lambda: self.saveButton.setEnabled(True))
        tabs.addTab(self.playersTab, "Players")
        tabs.addTab(SquadRolesTab(self.model.roles), "Roles")
        tabs.addTab(SquadAnalysisTab(), "Analysis")
        return tabs

    ## actions

    def _saveRequest(self) -> None:
        model: SquadModel = self.playersTab.modelBuild()
        self.modelSaveRequested.emit(model)

    def _tacticChange(self, tacticName: str) -> None:
        if self.model is None or tacticName == self.model.tacticName:
            return
        if tacticName in self.model.availableTactics:
            self.tacticSelected.emit(self.squadName, tacticName)

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
