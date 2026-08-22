"""FMSAT-intelligence presentation for the squad Analysis workspace."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from fmsat.app.presentation import playerNameDisplay
from fmsat.app.squadDetailModel import SquadDetailModel
from fmsat.app.squadDetailTabOverrides import SquadAnalysisTab as BaseSquadAnalysisTab
from fmsat.core.bestXi import BestXiAssignmentService
from fmsat.core.config import AttributeDefinition
from fmsat.tactics.positionFamily import playerPositionFamilies, positionFamilyFor


class SquadAnalysisTab(BaseSquadAnalysisTab):
    """Present simultaneous slot depth and the Generic Role Fit Best XI."""

    reassessRequested = Signal()
    regenerateRequested = Signal()

    def __init__(
        self,
        model: SquadDetailModel,
        attributes: tuple[AttributeDefinition, ...] = (),
        requiredRows: tuple[tuple[str, str], ...] = (),
        parent=None,
    ) -> None:
        super().__init__(model, attributes, requiredRows, parent)
        self._playerStrengthsSimplify()
        self._findingPlayerListsFormat()
        if model.requiredSlots:
            self._slotDepthPopulate(model)
        self._bestXiBuild(model)
        self._quadrantsArrange()
        self._analysisActionsAdd()

    def _analysisActionsAdd(self) -> None:
        """Keep evidence reinterpretation beside the heavier regeneration action."""

        actions = QHBoxLayout()
        actions.addStretch()
        self.regenerateButton = QPushButton("Regenerate Squad Model")
        self.regenerateButton.setToolTip(
            "Re-read the saved squad screenshots with the current parser and rebuild the squad model."
        )
        self.regenerateButton.clicked.connect(self.regenerateRequested.emit)
        actions.addWidget(self.regenerateButton)
        self.reassessButton = QPushButton("Reassess Squad")
        self.reassessButton.setToolTip(
            "Recalculate Analysis from saved player evidence using the latest role definitions and weights."
        )
        self.reassessButton.clicked.connect(self.reassessRequested.emit)
        actions.addWidget(self.reassessButton)
        root = self.layout()
        root.insertLayout(max(0, root.count() - 1), actions)

    def _playerStrengthsSimplify(self) -> None:
        """Keep Analysis conclusion-focused; detailed weighting remains on the Roles tab."""

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
        self.depthTable.setHorizontalHeaderLabels(("IP Role", "OOP Role", "Primary", "Backup"))
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

    def _bestXiBuild(self, model: SquadDetailModel) -> None:
        """Build Best XI from a whole-team assignment rather than slot-order greed."""

        self.bestXiTable = QTableWidget(0, 5, self)
        self.bestXiTable.setObjectName("roleDepthAnalysisTable")
        self.bestXiTable.setAlternatingRowColors(True)
        self.bestXiTable.setHorizontalHeaderLabels(
            ("Position", "IP Role", "OOP Role", "Selected Player", "Position Status")
        )
        self.bestXiTable.setWordWrap(False)
        self.bestXiTable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.bestXiTable.verticalHeader().setDefaultSectionSize(28)
        self.bestXiTable.setRowCount(len(model.requiredSlots))

        assignment = BestXiAssignmentService().assignmentBuild(
            model.requiredSlots,
            model.roles,
        )
        playersByDisplayName = {
            playerNameDisplay(player.name).casefold(): player for player in model.squad.players
        }
        for row, slot in enumerate(model.requiredSlots):
            selection = assignment.selectionFor(row)
            if selection is not None:
                selectedDisplay = selection.playerName
                player = playersByDisplayName.get(selectedDisplay.casefold())
                selectedEvidence = selection.evidence
            elif assignment.evidenceAvailable:
                selectedDisplay = (
                    "Unavailable"
                    if str(slot.primary).strip().casefold() == "unavailable"
                    else "Uncovered"
                )
                player = None
                selectedEvidence = (
                    "No unique-player global assignment has complete calculable role-fit "
                    "evidence for this slot."
                )
            else:
                # Preserve legacy presentation only when the optimiser has no role-candidate
                # evidence at all (primarily old fixtures and incomplete stored models).
                selectedDisplay, player = self._selectedPlayerResolve(
                    slot.primary,
                    playersByDisplayName,
                )
                selectedEvidence = slot.primaryEvidence

            positionStatus, positionEvidence = self._selectionPositionStatus(
                selectedDisplay,
                slot.position,
                player,
            )
            values = (
                slot.position,
                slot.ipRole,
                slot.oopRole,
                selectedDisplay,
                positionStatus,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 3:
                    item.setToolTip(selectedEvidence)
                elif column == 4:
                    item.setToolTip(positionEvidence)
                else:
                    item.setToolTip(slot.position)
                self.bestXiTable.setItem(row, column, item)
            self.bestXiTable.setRowHeight(row, 28)

        header = self.bestXiTable.horizontalHeader()
        for column in range(4):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

    def _quadrantsArrange(self) -> None:
        """Arrange the four analysis conclusions as a balanced 2x2 dashboard."""

        root = self.layout()
        if root is None:
            return
        context = root.itemAt(0).widget() if root.count() else None

        for table in (self.bestXiTable, self.depthTable, self.playerTable, self.findingsTable):
            table.setParent(self)
        while root.count():
            item = root.takeAt(0)
            widget = item.widget()
            if widget is context:
                continue
            self._layoutItemDiscard(item)

        if context is not None:
            context.setParent(self)
            root.addWidget(context)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.addWidget(self._cardCreate("Best XI — Generic Role Fit", self.bestXiTable), 0, 0)
        grid.addWidget(self._cardCreate("Required Role Depth", self.depthTable), 0, 1)
        grid.addWidget(self._cardCreate("Player Role Strengths", self.playerTable), 1, 0)
        grid.addWidget(self._cardCreate("Squad Depth Findings", self.findingsTable), 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        root.addLayout(grid, 1)

    @staticmethod
    def _layoutItemDiscard(item) -> None:
        """Dispose obsolete dashboard wrappers without deleting re-parented tables."""

        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
            return
        layout = item.layout()
        if layout is None:
            return
        while layout.count():
            SquadAnalysisTab._layoutItemDiscard(layout.takeAt(0))
        layout.deleteLater()

    @staticmethod
    def _selectedPlayerResolve(selected: str, playersByDisplayName: dict[str, object]):
        """Resolve Role Depth presentation text back to its squad-player identity."""

        selectedText = str(selected or "").strip()
        selectedKey = selectedText.casefold()
        player = playersByDisplayName.get(selectedKey)
        if player is not None:
            return selectedText, player

        for displayKey, candidate in playersByDisplayName.items():
            if selectedKey.startswith(f"{displayKey} · "):
                return playerNameDisplay(candidate.name), candidate
        return selectedText, None

    @staticmethod
    def _selectionPositionStatus(
        selected: str,
        position: str,
        player,
    ) -> tuple[str, str]:
        """Keep non-player Best XI states separate from positional familiarity."""

        selectedState = str(selected or "").strip().casefold()
        if selectedState == "uncovered":
            return "Uncovered", "No player was selected for this tactic slot."
        if selectedState in {"unavailable", "—", ""}:
            return "—", "No selected player is available for familiarity assessment."
        return SquadAnalysisTab._positionStatus(position, player)

    @staticmethod
    def _positionStatus(position: str, player) -> tuple[str, str]:
        """Compare the tactic slot family with positions captured from squad screenshots."""

        if player is None:
            return (
                "Familiarity unavailable",
                "The selected player or their positional evidence is unavailable.",
            )
        captured = str(player.positions or "").strip()
        if not captured:
            return (
                "Familiarity unavailable",
                "No player positions were captured from the squad screenshots.",
            )

        requiredFamily = positionFamilyFor(position)
        capturedFamilies = playerPositionFamilies(captured)
        if requiredFamily is None:
            return (
                "Familiarity unavailable",
                f"Required position {position} has no confirmed position-family mapping.",
            )
        if not capturedFamilies:
            return (
                "Familiarity unavailable",
                f"Captured positions ({captured}) could not be mapped to confirmed position families.",
            )
        if requiredFamily in capturedFamilies:
            return (
                "Familiar",
                f"Required position {position} ({requiredFamily.value}) is covered by captured "
                f"positions: {captured}.",
            )
        return (
            "Training required",
            f"This player has the attributes for this role but {position} "
            f"({requiredFamily.value}) is not covered by captured positions ({captured}). "
            "Positional training would be required.",
        )
