"""Focused presentation refinements for the requirement 007 squad tabs."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHeaderView, QTableWidget

from fmsat.app.squadDetailModel import RoleDisplay, SquadDetailModel
from fmsat.app.squadDetailTabs import (
    SquadAnalysisTab as BaseSquadAnalysisTab,
    SquadRolesTab as BaseSquadRolesTab,
)
from fmsat.core.config import AttributeDefinition


class SquadRolesTab(BaseSquadRolesTab):
    """Keep role rows compact and render attribute names as presentation abbreviations."""

    def __init__(
        self,
        roles: tuple[RoleDisplay, ...],
        attributes: tuple[AttributeDefinition, ...] = (),
        parent=None,
    ) -> None:
        self.attributeAbbreviations = {
            attribute.name: attribute.abbreviation for attribute in attributes
        }
        super().__init__(roles, parent)
        if not hasattr(self, "candidateTable"):
            return
        self.candidateTable.setWordWrap(False)
        self.candidateTable.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed
        )
        self.candidateTable.verticalHeader().setDefaultSectionSize(28)
        self.roleTable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.roleTable.verticalHeader().setDefaultSectionSize(28)
        self._breakdownsAbbreviate(self.candidateTable, 4)
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
        self._breakdownsAbbreviate(self.candidateTable, 4)
        self._rowsCompact()

    def _rowsCompact(self) -> None:
        """Use stable one-line heights even when the tab was initially hidden."""

        for table in (self.roleTable, self.candidateTable):
            for row in range(table.rowCount()):
                table.setRowHeight(row, 28)

    def _breakdownsAbbreviate(self, table: QTableWidget, column: int) -> None:
        for row in range(table.rowCount()):
            item = table.item(row, column)
            if item is None:
                continue
            original = item.text()
            item.setToolTip(original)
            item.setText(self._attributeTextAbbreviate(original))

    def _attributeTextAbbreviate(self, text: str) -> str:
        for name, abbreviation in self.attributeAbbreviations.items():
            text = text.replace(f"{name}:", f"{abbreviation}:")
            text = text.replace(f"{name},", f"{abbreviation},")
        return text


class SquadAnalysisTab(BaseSquadAnalysisTab):
    """Show tactical-slot depth while keeping evidence tables compact."""

    def __init__(
        self,
        model: SquadDetailModel,
        attributes: tuple[AttributeDefinition, ...] = (),
        parent=None,
    ) -> None:
        self.attributeAbbreviations = {
            attribute.name: attribute.abbreviation for attribute in attributes
        }
        super().__init__(model, parent)
        self._depthExpand(model)
        self._compactTable(self.playerTable)
        self._compactTable(self.findingsTable)
        self._breakdownsAbbreviate(self.playerTable, 3)
        self._tooltipsApply(self.findingsTable, 2)
        QTimer.singleShot(0, self._rowsCompact)

    def _depthExpand(self, model: SquadDetailModel) -> None:
        """Present one depth row per tactical position rather than per unique role."""

        rows: list[tuple[str, str]] = []
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

    def _rowsCompact(self) -> None:
        for table in (self.depthTable, self.playerTable, self.findingsTable):
            for row in range(table.rowCount()):
                table.setRowHeight(row, 28)

    def _breakdownsAbbreviate(self, table: QTableWidget, column: int) -> None:
        for row in range(table.rowCount()):
            item = table.item(row, column)
            if item is None:
                continue
            original = item.text()
            item.setToolTip(original)
            for name, abbreviation in self.attributeAbbreviations.items():
                original = original.replace(f"{name}:", f"{abbreviation}:")
                original = original.replace(f"{name},", f"{abbreviation},")
            item.setText(original)

    @staticmethod
    def _tooltipsApply(table: QTableWidget, column: int) -> None:
        for row in range(table.rowCount()):
            item = table.item(row, column)
            if item is not None:
                item.setToolTip(item.text())
