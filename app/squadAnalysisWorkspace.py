"""FMSAT-intelligence presentation for the squad Analysis workspace."""

from __future__ import annotations

from PySide6.QtWidgets import QHeaderView, QTableWidgetItem

from fmsat.app.squadDetailModel import SquadDetailModel
from fmsat.app.squadDetailTabOverrides import SquadAnalysisTab as BaseSquadAnalysisTab
from fmsat.core.config import AttributeDefinition


class SquadAnalysisTab(BaseSquadAnalysisTab):
    """Present simultaneous slot depth produced by the core RoleDepthService."""

    def __init__(
        self,
        model: SquadDetailModel,
        attributes: tuple[AttributeDefinition, ...] = (),
        requiredRows: tuple[tuple[str, str], ...] = (),
        parent=None,
    ) -> None:
        # The base class still owns the dashboard composition and companion analysis tables.
        super().__init__(model, attributes, requiredRows, parent)
        self._playerStrengthsSimplify()
        self._findingPlayerListsFormat()
        if model.requiredSlots:
            self._slotDepthPopulate(model)

    def _playerStrengthsSimplify(self) -> None:
        """Keep Analysis conclusion-focused; detailed weighting remains on the Roles tab."""

        # Score breakdown is valuable evidence, but the Roles workspace already exposes it
        # in detail. Analysis should prioritise role conclusions and squad-level patterns.
        if self.playerTable.columnCount() >= 5:
            self.playerTable.removeColumn(3)
        header = self.playerTable.horizontalHeader()
        for column in range(min(3, self.playerTable.columnCount())):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        if self.playerTable.columnCount() >= 4:
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

    def _findingPlayerListsFormat(self) -> None:
        """Separate surname-first player names with semicolons in finding prose."""

        for row in range(self.findingsTable.rowCount()):
            item = self.findingsTable.item(row, 2)
            if item is None:
                continue
            text = item.text()
            if "players have this as their best role" not in text or ": " not in text:
                continue
            prefix, namesText = text.rsplit(": ", 1)
            suffix = "." if namesText.endswith(".") else ""
            if suffix:
                namesText = namesText[:-1]
            parts = [part.strip() for part in namesText.split(",") if part.strip()]
            if len(parts) < 4 or len(parts) % 2:
                continue
            names = [f"{parts[index]}, {parts[index + 1]}" for index in range(0, len(parts), 2)]
            item.setText(f"{prefix}: {'; '.join(names)}{suffix}")

    def _slotDepthPopulate(self, model: SquadDetailModel) -> None:
        """Render hidden-position-ordered IP/OOP roles with primary and backup assignments."""

        self.depthTable.clearContents()
        self.depthTable.setColumnCount(4)
        self.depthTable.setHorizontalHeaderLabels(
            ("IP Role", "OOP Role", "Primary", "Backup")
        )
        self.depthTable.setRowCount(len(model.requiredSlots))

        for row, slot in enumerate(model.requiredSlots):
            values = (slot.ipRole, slot.oopRole, slot.primary, slot.backup)
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 2:
                    item.setToolTip(slot.primaryEvidence)
                elif column == 3:
                    item.setToolTip(slot.backupEvidence)
                else:
                    item.setToolTip(slot.position)
                self.depthTable.setItem(row, column, item)
            self.depthTable.setRowHeight(row, 28)

        header = self.depthTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
