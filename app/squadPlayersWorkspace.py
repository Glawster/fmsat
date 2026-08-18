"""Player-table presentation rules for the squad workspace."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker

from fmsat.app.presentation import playerNameDisplay, playerNameStorage
from fmsat.app.squadDetailTabOverrides import SquadPlayersTab as BaseSquadPlayersTab
from fmsat.core.config import AttributeDefinition
from fmsat.core.squadModel import SquadModel


class SquadPlayersTab(BaseSquadPlayersTab):
    """Show surname-first names while preserving stored player identity on save."""

    def __init__(
        self,
        model: SquadModel,
        attributes: tuple[AttributeDefinition, ...] = (),
        parent=None,
    ) -> None:
        super().__init__(model, attributes, parent)
        blocker = QSignalBlocker(self.table)
        self.table.setSortingEnabled(False)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None:
                item.setText(playerNameDisplay(item.text()))
        self.table.setSortingEnabled(True)
        del blocker

    def _text(self, row: int, column: int) -> str:
        """Translate the editable surname-first display back to stored name order."""

        value = super()._text(row, column)
        return playerNameStorage(value) if column == 0 else value
