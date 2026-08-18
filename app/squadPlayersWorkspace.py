"""Player-table presentation and player-editor workflow for the squad workspace."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QDialog

from fmsat.app.playerEditorDialog import PlayerEditorDialog
from fmsat.app.presentation import playerNameDisplay, playerNameStorage
from fmsat.app.squadDetailTabOverrides import SquadPlayersTab as BaseSquadPlayersTab
from fmsat.core.config import AttributeDefinition
from fmsat.core.squadModel import SquadModel, SquadModelPlayer


class SquadPlayersTab(BaseSquadPlayersTab):
    """Browse squad facts and open one focused editor per player."""

    playerSaveRequested = Signal()

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
                item.setToolTip("Double-click this row to edit the player")
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        del blocker
        self.table.cellDoubleClicked.connect(self._playerEditorOpen)

    def _text(self, row: int, column: int) -> str:
        """Translate the surname-first display back to stored name order."""

        value = super()._text(row, column)
        return playerNameStorage(value) if column == 0 else value

    def _traitEditorOpen(self, _row: int, _column: int) -> None:
        """Disable the legacy single-cell trait editor; Player Editor owns all edits."""

        return

    def _playerEditorOpen(self, row: int, _column: int) -> None:
        """Open one factual player editor and immediately persist accepted changes."""

        player = self._playerAtRow(row)
        dialog = PlayerEditorDialog(player, self.attributes, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        edited = dialog.editedPlayer()
        self._playerRowApply(row, edited)
        self.changed.emit()

        # MainWindow already owns squad persistence and assessment refresh. Reuse it so
        # role scores, slot depth and findings are rebuilt from the corrected facts once.
        save = getattr(self.window(), "_squadModelSave", None)
        if callable(save):
            save(self.modelBuild())
        else:
            self.playerSaveRequested.emit()

    def _playerAtRow(self, row: int) -> SquadModelPlayer:
        """Rebuild one visible row into a detached player while retaining provenance."""

        sourceItem = self.table.item(row, 0)
        if sourceItem is None:
            raise ValueError("Player row is unavailable")
        sourceIndex = int(sourceItem.data(Qt.ItemDataRole.UserRole))
        original = self.model.players[sourceIndex]
        attributes = []
        for column, attribute in enumerate(self.attributeNames, start=4):
            text = self._text(row, column)
            attributes.append((attribute, int(text) if text else None))
        traits = tuple(
            value.strip()
            for value in self._text(row, self.table.columnCount() - 1).split(",")
            if value.strip()
        )
        return SquadModelPlayer(
            name=self._text(row, 0),
            positions=self._text(row, 1),
            ca=self._text(row, 2),
            pa=self._text(row, 3),
            confidence=original.confidence,
            sourceImportSessionId=original.sourceImportSessionId,
            validationState=original.validationState,
            attributes=tuple(attributes),
            traits=traits,
        )

    def _playerRowApply(self, row: int, player: SquadModelPlayer) -> None:
        """Reflect accepted editor facts in the browse table before model persistence."""

        sourceItem = self.table.item(row, 0)
        if sourceItem is None:
            return
        sourceIndex = sourceItem.data(Qt.ItemDataRole.UserRole)
        blocker = QSignalBlocker(self.table)
        sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.table.item(row, 0).setText(playerNameDisplay(player.name))
        self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, sourceIndex)
        self.table.item(row, 1).setText(player.positions)
        self.table.item(row, 2).setText(player.ca)
        self.table.item(row, 3).setText(player.pa)
        values = dict(player.attributes)
        for column, attribute in enumerate(self.attributeNames, start=4):
            value = values.get(attribute)
            self.table.item(row, column).setText("" if value is None else str(value))
        traitsColumn = self.table.columnCount() - 1
        self.table.item(row, traitsColumn).setText(", ".join(player.traits))
        self.table.setSortingEnabled(sorting)
        del blocker
