"""Focused presentation refinements for the requirement 007 squad tabs."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
)

from fmsat.app.squadDetailModel import RoleDisplay, SquadDetailModel
from fmsat.app.squadDetailTabs import (
    SquadAnalysisTab as BaseSquadAnalysisTab,
    SquadRolesTab as BaseSquadRolesTab,
)
from fmsat.core.config import AttributeDefinition


class SquadRolesTab(BaseSquadRolesTab):
    """Keep role rows compact while retaining descriptive calculation text."""

    def __init__(
        self,
        roles: tuple[RoleDisplay, ...],
        attributes: tuple[AttributeDefinition, ...] = (),
        parent=None,
    ) -> None:
        super().__init__(roles, parent)
        if not hasattr(self, "candidateTable"):
            return
        self.candidateTable.setWordWrap(False)
        self.candidateTable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.candidateTable.verticalHeader().setDefaultSectionSize(28)
        self.roleTable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.roleTable.verticalHeader().setDefaultSectionSize(28)
        self._tooltipsApply(self.candidateTable, 4)
        QTimer.singleShot(0, self._rowsCompact)

    def _roleShow(
        self,
        currentRow: int,
        currentColumn: int,
        previousRow: int,
        previousColumn: int,
    ) -> None:
        super()._roleShow(currentRow, currentColumn, previousRow, previousColumn)
        if not hasattr(self, "candidateTable"):
            return
        self._tooltipsApply(self.candidateTable, 4)
        self._rowsCompact()

    def _rowsCompact(self) -> None:
        """Use stable one-line heights even when the tab was initially hidden."""

        for table in (self.roleTable, self.candidateTable):
            for row in range(table.rowCount()):
                table.setRowHeight(row, 28)

    @staticmethod
    def _tooltipsApply(table: QTableWidget, column: int) -> None:
        for row in range(table.rowCount()):
            item = table.item(row, column)
            if item is not None:
                item.setToolTip(item.text())


class SquadAnalysisTab(BaseSquadAnalysisTab):
    """Show the three analysis areas as side-by-side dashboard cards."""

    def __init__(
        self,
        model: SquadDetailModel,
        attributes: tuple[AttributeDefinition, ...] = (),
        requiredRows: tuple[tuple[str, str], ...] = (),
        parent=None,
    ) -> None:
        super().__init__(model, parent)
        self._depthExpand(model, requiredRows)
        self._compactTable(self.depthTable)
        self._compactTable(self.playerTable)
        self._compactTable(self.findingsTable)
        self._tooltipsApply(self.playerTable, 3)
        self._tooltipsApply(self.findingsTable, 2)
        self._horizontalCardsArrange()
        QTimer.singleShot(0, self._rowsCompact)

    def _depthExpand(
        self,
        model: SquadDetailModel,
        requiredRows: tuple[tuple[str, str], ...],
    ) -> None:
        """Present one depth row per tactical player slot, retaining repeated roles."""

        rows = list(requiredRows)
        if not rows:
            for role in model.roles:
                positions = tuple(
                    value.strip() for value in role.positions.split(",") if value.strip()
                ) or ("",)
                for position in positions:
                    label = role.abbreviation
                    if position:
                        label += f" · {position}"
                    label += f" — {role.displayName}"
                    rows.append((label, role.coverage))

        self.depthTable.setRowCount(len(rows))
        for row, (label, coverage) in enumerate(rows):
            self.depthTable.setItem(row, 0, self._item(label))
            self.depthTable.setItem(row, 1, self._item(coverage))
        self.depthTable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.depthTable.verticalHeader().setDefaultSectionSize(28)

    @staticmethod
    def _item(text: str):
        from PySide6.QtWidgets import QTableWidgetItem

        return QTableWidgetItem(text)

    @staticmethod
    def _compactTable(table: QTableWidget) -> None:
        table.setWordWrap(False)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _horizontalCardsArrange(self) -> None:
        """Replace the vertical report stack with three independently scrolling cards."""

        root = self.layout()
        if root is None:
            return
        context = root.itemAt(0).widget() if root.count() else None
        while root.count():
            item = root.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not context and widget not in {
                self.depthTable,
                self.playerTable,
                self.findingsTable,
            }:
                widget.deleteLater()
        if context is not None:
            context.setParent(self)
            root.addWidget(context)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        cards.addWidget(self._cardCreate("Required Role Depth", self.depthTable), 3)
        cards.addWidget(self._cardCreate("Player Role Strengths", self.playerTable), 4)
        cards.addWidget(self._cardCreate("Squad Depth Findings", self.findingsTable), 3)
        root.addLayout(cards, 1)

    def _cardCreate(self, title: str, table: QTableWidget) -> QFrame:
        card = QFrame(self)
        card.setObjectName("overviewPanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        heading = QLabel(title, card)
        heading.setObjectName("cardTitle")
        layout.addWidget(heading)
        table.setParent(card)
        layout.addWidget(table, 1)
        return card

    def _rowsCompact(self) -> None:
        for table in (self.depthTable, self.playerTable, self.findingsTable):
            for row in range(table.rowCount()):
                table.setRowHeight(row, 28)

    @staticmethod
    def _tooltipsApply(table: QTableWidget, column: int) -> None:
        for row in range(table.rowCount()):
            item = table.item(row, column)
            if item is not None:
                item.setToolTip(item.text())
