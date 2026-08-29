"""Tactic Analysis tab: 009 empty shell, or 011 demand dashboard."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.tacticAnalysisDisplay import TacticAnalysisDisplay, tacticAnalysisDisplayBuild
from fmsat.core.tacticAnalysis import TacticAnalysis


class AnalysisTab(QWidget):
    """Present tactic demand, or the 009 empty shell when no model exists."""

    reanalyseRequested = Signal()

    def __init__(
        self,
        analysis: TacticAnalysis | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if analysis is None:
            self._emptyStateBuild()
            return
        self._dashboardBuild(tacticAnalysisDisplayBuild(analysis))

    def _emptyStateBuild(self) -> None:
        """009 empty shell: generated analysis is not imported fact."""

        layout = QVBoxLayout(self)
        layout.addStretch()
        icon = QLabel("◇")
        icon.setObjectName("emptyIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)
        title = QLabel("Analysis Is Ready When You Are")
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        copy = QLabel(
            "Generated analysis will appear here, clearly separated from imported and "
            "user-entered facts. No tactical conclusions have been generated yet."
        )
        copy.setObjectName("mutedText")
        copy.setWordWrap(True)
        copy.setMaximumWidth(560)
        copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyRow = QHBoxLayout()
        copyRow.addStretch()
        copyRow.addWidget(copy)
        copyRow.addStretch()
        layout.addLayout(copyRow)
        layout.addStretch()

    def _dashboardBuild(self, display: TacticAnalysisDisplay) -> None:
        layout = QVBoxLayout(self)
        banner = QLabel(display.banner)
        banner.setObjectName("mutedText")
        banner.setWordWrap(True)
        layout.addWidget(banner)
        layout.addWidget(self._requirementsCard(display), 2)
        lower = QHBoxLayout()
        lower.addWidget(self._demandCard(display), 1)
        lower.addWidget(self._observationsCard(display), 1)
        layout.addLayout(lower, 2)
        actions = QHBoxLayout()
        actions.addStretch()
        self.reanalyseButton = QPushButton("Reanalyse Tactic")
        self.reanalyseButton.setObjectName("reanalyseTacticButton")
        self.reanalyseButton.setToolTip(
            "Recalculate tactic demand from the saved football object model using the "
            "current role-assessment policy. Does not regenerate screenshots."
        )
        self.reanalyseButton.clicked.connect(self.reanalyseRequested.emit)
        actions.addWidget(self.reanalyseButton)
        layout.addLayout(actions)

    def _requirementsCard(self, display: TacticAnalysisDisplay) -> QFrame:
        table = self._table(
            ("Position", "IP Role", "OOP Role", "Transition", "Evidence"),
            "tacticRoleRequirementsTable",
        )
        table.setRowCount(len(display.slots))
        for row, slot in enumerate(display.slots):
            values = (slot.position, slot.ipRole, slot.oopRole, slot.transition, slot.evidence)
            tips = (
                slot.positionToolTip,
                slot.ipToolTip,
                slot.oopToolTip,
                slot.transition,
                slot.evidenceToolTip,
            )
            for column, (value, tip) in enumerate(zip(values, tips)):
                item = QTableWidgetItem(value)
                item.setToolTip(tip)
                table.setItem(row, column, item)
            table.setRowHeight(row, 28)
        header = table.horizontalHeader()
        for column in range(4):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        return self._card("Role Requirements", table)

    def _demandCard(self, display: TacticAnalysisDisplay) -> QFrame:
        if not display.demand:
            label = QLabel("Unavailable")
            label.setObjectName("mutedText")
            return self._card("Attribute Demand", label)
        table = self._table(("Attribute", "Overall", "IP", "OOP"), "tacticDemandTable")
        table.setRowCount(len(display.demand))
        for row, item in enumerate(display.demand):
            values = (item.attribute, item.overall, item.inPossession, item.outOfPossession)
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setToolTip(item.toolTip)
                if column > 0:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, column, cell)
            table.setRowHeight(row, 28)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 4):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        return self._card("Attribute Demand", table)

    def _observationsCard(self, display: TacticAnalysisDisplay) -> QFrame:
        if not display.observations:
            label = QLabel(
                "No repeated roles, flank mismatches, or classifiable family "
                "changes were identified."
            )
            label.setObjectName("mutedText")
            label.setWordWrap(True)
            return self._card("Structural Observations", label)
        table = self._table(("Finding", "Evidence"), "tacticObservationsTable")
        table.setRowCount(len(display.observations))
        for row, item in enumerate(display.observations):
            table.setItem(row, 0, QTableWidgetItem(item.finding))
            table.setItem(row, 1, QTableWidgetItem(item.evidence))
            table.setRowHeight(row, 28)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        return self._card("Structural Observations", table)

    @staticmethod
    def _card(title: str, widget: QWidget) -> QFrame:
        panel = QFrame()
        panel.setObjectName("overviewPanel")
        layout = QVBoxLayout(panel)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        layout.addWidget(heading)
        layout.addWidget(widget)
        return panel

    def _table(self, headers: tuple[str, ...], objectName: str) -> QTableWidget:
        table = QTableWidget(0, len(headers), self)
        table.setObjectName(objectName)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setWordWrap(False)
        return table
