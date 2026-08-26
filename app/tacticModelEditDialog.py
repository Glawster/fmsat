"""Controlled editor for the current tactic object model."""

from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.adminWidgets import AdminEditDialog, adminTableConfigure
from fmsat.tactics.tactic import Tactic


class TacticModelEditDialog(AdminEditDialog):
    """Edit observed role-level tactic facts without rewriting screenshots."""

    def __init__(self, tactic: Tactic, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.sourceTactic = tactic
        self.editedTactic: Tactic | None = None
        self.setWindowTitle("Edit Tactic Model")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        explanation = QLabel(
            "Correct the current object model below. Role is the assessment identity; "
            "position remains its tactic context. Saving retains the source screenshots "
            "and marks them as superseded."
        )
        explanation.setObjectName("adminHelpText")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        tabs = QTabWidget(self)
        tabs.setObjectName("adminTabs")
        self.rolesTable = self._rolesTableCreate()
        self.instructionsTable = self._instructionsTableCreate()
        tabs.addTab(self.rolesTable, "Roles")
        tabs.addTab(self.instructionsTable, "Instructions")
        layout.addWidget(tabs, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._modelAccept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _rolesTableCreate(self) -> QTableWidget:
        rows = sum(
            len(formation.positions)
            for formation in (
                self.sourceTactic.inPossession,
                self.sourceTactic.outOfPossession,
            )
        )
        table = QTableWidget(rows, 7, self)
        table.setObjectName("adminModelTable")
        table.setHorizontalHeaderLabels(
            ("Phase", "Slot", "Position", "Canonical role", "Duty", "X", "Y")
        )
        row = 0
        for phase, formation in (
            ("In Possession", self.sourceTactic.inPossession),
            ("Out Of Possession", self.sourceTactic.outOfPossession),
        ):
            for position in formation.positions:
                values = (
                    phase,
                    position.slotId or "",
                    position.canonicalPosition or position.identity.value,
                    position.canonicalRole or "",
                    position.duty or "",
                    "" if position.x is None else str(position.x),
                    "" if position.y is None else str(position.y),
                )
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if column < 2:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, column, item)
                row += 1

        # Slot, Position and Duty are short identifiers; the descriptive phase,
        # role and coordinate fields share the remaining frame width.
        adminTableConfigure(table, compactColumns=(1, 2, 4))
        return table

    def _instructionsTableCreate(self) -> QTableWidget:
        items = [
            (phase, instruction.name, value.name)
            for phase, instructionSet in (
                ("In Possession", self.sourceTactic.inPossession.instructions),
                ("Out Of Possession", self.sourceTactic.outOfPossession.instructions),
                ("Transition", self.sourceTactic.transition.instructions),
            )
            for instruction, value in sorted(
                instructionSet.items(), key=lambda item: item[0].name.casefold()
            )
        ]
        table = QTableWidget(len(items), 3, self)
        table.setObjectName("adminModelTable")
        table.setHorizontalHeaderLabels(("Phase", "Instruction", "Selected value"))
        for row, values in enumerate(items):
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column < 2:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, column, item)
        adminTableConfigure(table)
        return table

    def _modelAccept(self) -> None:
        try:
            tactic = deepcopy(self.sourceTactic)
            positions = [
                *tactic.inPossession.positions,
                *tactic.outOfPossession.positions,
            ]
            for row, position in enumerate(positions):
                position.canonicalPosition = self._text(self.rolesTable, row, 2)
                position.canonicalRole = self._text(self.rolesTable, row, 3)
                position.duty = self._text(self.rolesTable, row, 4) or None
                position.x = self._float(self._text(self.rolesTable, row, 5))
                position.y = self._float(self._text(self.rolesTable, row, 6))

            row = 0
            for instructionSet in (
                tactic.inPossession.instructions,
                tactic.outOfPossession.instructions,
                tactic.transition.instructions,
            ):
                for instruction in sorted(instructionSet, key=lambda item: item.name.casefold()):
                    current = instructionSet[instruction]
                    instructionSet[instruction] = type(current)(
                        self._text(self.instructionsTable, row, 2),
                        current.description,
                    )
                    row += 1
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid tactic value", str(exc))
            return
        self.editedTactic = tactic
        self.accept()

    @staticmethod
    def _text(table: QTableWidget, row: int, column: int) -> str:
        item = table.item(row, column)
        return item.text().strip() if item is not None else ""

    @staticmethod
    def _float(value: str) -> float | None:
        if not value:
            return None
        parsed = float(value)
        if not 0.0 <= parsed <= 1.0:
            raise ValueError("Tactic coordinates must be between 0 and 1")
        return parsed
