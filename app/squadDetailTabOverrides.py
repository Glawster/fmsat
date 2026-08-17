"""Focused presentation refinements for the requirement 007 squad tabs."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from fmsat.app.squadDetailModel import CandidateDisplay, RoleDisplay, SquadDetailModel
from fmsat.app.squadDetailTabs import (
    SortableTableWidgetItem,
    SquadAnalysisTab as BaseSquadAnalysisTab,
    SquadPlayersTab as BaseSquadPlayersTab,
    SquadRolesTab as BaseSquadRolesTab,
)
from fmsat.core.config import AttributeDefinition
from fmsat.core.squadModel import SquadModel


def _breakdownAbbreviate(
    table: QTableWidget,
    column: int,
    attributes: tuple[AttributeDefinition, ...],
) -> None:
    """Render configured attribute abbreviations without changing score evidence."""

    abbreviations = {
        attribute.name: attribute.abbreviation
        for attribute in attributes
        if attribute.abbreviation.strip()
    }
    if not abbreviations:
        return
    for row in range(table.rowCount()):
        item = table.item(row, column)
        if item is None:
            continue
        original = item.toolTip() or item.text()
        rendered = original
        for name, abbreviation in sorted(
            abbreviations.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            rendered = rendered.replace(f"{name}:", f"{abbreviation}:")
        item.setText(rendered)
        item.setToolTip(original)


def _breakdownCompact(
    value: str,
    attributes: tuple[AttributeDefinition, ...],
) -> str:
    """Reduce detailed weighted arithmetic to attribute contribution percentages."""

    abbreviations = {
        attribute.name: attribute.abbreviation
        for attribute in attributes
        if attribute.abbreviation.strip()
    }
    percentages: list[str] = []
    for component in value.split(";"):
        match = re.match(
            r"\s*([^:]+):.*?=\s*([0-9]+(?:\.[0-9]+)?)/([0-9]+(?:\.[0-9]+)?)\s*$",
            component,
        )
        if match is None:
            continue
        name, numeratorText, denominatorText = match.groups()
        denominator = float(denominatorText)
        if denominator <= 0:
            continue
        abbreviation = abbreviations.get(name.strip(), name.strip())
        percentage = round(float(numeratorText) * 100 / denominator)
        percentages.append(f"{abbreviation}: {percentage}%")
    return ", ".join(percentages) if percentages else value


def _columnsLeftAlign(table: QTableWidget, columns: tuple[int, ...]) -> None:
    """Apply the shared table rule that names and positions read left-to-right."""

    alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    for row in range(table.rowCount()):
        for column in columns:
            item = table.item(row, column)
            if item is not None:
                item.setTextAlignment(alignment)


def _playerNameDisplay(name: str) -> str:
    """Render player names as surname, given names for compact picker browsing."""

    parts = name.split()
    if len(parts) < 2:
        return name
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def _playerNameSortKey(name: str) -> tuple[str, str]:
    """Sort picker names by surname while keeping the original identity stable."""

    parts = name.split()
    if len(parts) < 2:
        return (name.casefold(), "")
    return (parts[-1].casefold(), " ".join(parts[:-1]).casefold())


def _positionUnits(positions: str) -> set[str]:
    """Return broad FM positional units from compact natural-position text."""

    compact = re.sub(r"\s+", "", positions.upper())
    units: set[str] = set()
    if "GK" in compact:
        units.add("GK")
    if "WB" in compact:
        units.add("WB")
    if re.search(r"(?:^|[,/])D(?:\(|[LCR]|$)", compact):
        units.add("D")
    if "DM" in compact:
        units.add("DM")
    if re.search(r"(?:^|[,/])M(?:\(|[LCR]|$)", compact):
        units.add("M")
    if "AM" in compact:
        units.add("AM")
    if "ST" in compact:
        units.add("ST")
    return units


def _roleUnits(positions: str) -> set[str]:
    """Map canonical role positions to the same broad units used for players."""

    units: set[str] = set()
    for value in positions.split(","):
        compact = re.sub(r"[^A-Z]", "", value.upper())
        if compact == "GK":
            units.add("GK")
        elif compact.startswith("WB"):
            units.add("WB")
        elif compact.startswith("DM"):
            units.add("DM")
        elif compact.startswith("AM"):
            units.add("AM")
        elif compact.startswith("ST"):
            units.add("ST")
        elif compact.startswith("D"):
            units.add("D")
        elif compact.startswith("M"):
            units.add("M")
    return units


def _candidateEligible(role: RoleDisplay, candidate: CandidateDisplay) -> bool:
    """Keep role browsing position-aware without changing Generic Role Fit scoring."""

    required = _roleUnits(role.positions)
    available = _positionUnits(candidate.positions)
    if not required:
        return True
    if required == {"GK"}:
        return "GK" in available
    return bool(required.intersection(available)) and "GK" not in available


class SquadPlayersTab(BaseSquadPlayersTab):
    """Keep identity columns left aligned while compact data remains centred."""

    def __init__(
        self,
        model: SquadModel,
        attributes: tuple[AttributeDefinition, ...] = (),
        parent=None,
    ) -> None:
        super().__init__(model, attributes, parent)
        _columnsLeftAlign(self.table, (0, 1))


class SquadRolesTab(BaseSquadRolesTab):
    """Provide role-to-player and player-to-role browsing from one assessment surface."""

    def __init__(
        self,
        roles: tuple[RoleDisplay, ...],
        attributes: tuple[AttributeDefinition, ...] = (),
        parent=None,
    ) -> None:
        self.attributes = attributes
        super().__init__(roles, parent)
        if not hasattr(self, "candidateTable"):
            return

        self.roleTable.clearSelection()
        self.roleTable.setCurrentCell(-1, -1)
        self.roleTable.setMinimumWidth(390)
        self.roleTable.setColumnWidth(2, 210)
        self.candidateTable.setWordWrap(False)
        self.candidateTable.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed
        )
        self.candidateTable.verticalHeader().setDefaultSectionSize(28)
        self.roleTable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.roleTable.verticalHeader().setDefaultSectionSize(28)
        splitter = self.roleTable.parentWidget()
        if splitter is not None and hasattr(splitter, "setSizes"):
            splitter.setSizes([420, 980])

        self.clearRoleButton = QPushButton("Show all players / roles", self)
        self.clearRoleButton.setObjectName("secondaryButton")
        self.clearRoleButton.clicked.connect(self._selectionClear)
        root = self.layout()
        if root is not None:
            root.insertWidget(0, self.clearRoleButton, 0, Qt.AlignmentFlag.AlignLeft)

            titles = QHBoxLayout()
            titles.setSpacing(12)
            self.rolePaneTitle = QLabel("Tactic Roles", self)
            self.rolePaneTitle.setObjectName("workspaceHeading")
            titles.addWidget(self.rolePaneTitle, 3)
            self.candidatePaneTitle = QLabel("Candidates for Selected Role", self)
            self.candidatePaneTitle.setObjectName("workspaceHeading")
            titles.addWidget(self.candidatePaneTitle, 7)
            root.insertLayout(1, titles)

        self.playerRoleTitle = QLabel("Player Role Assessment", self)
        self.playerRoleTitle.setObjectName("workspaceHeading")
        self.playerPicker = QComboBox(self)
        self.playerPicker.setObjectName("rolePlayerPicker")
        self.playerPicker.setMaximumWidth(320)
        self.playerPicker.addItem("Select a player…", "")
        for name in sorted(self._allPlayerNames(), key=_playerNameSortKey):
            self.playerPicker.addItem(_playerNameDisplay(name), name)

        self.playerRoleTable = QTableWidget(0, 4, self)
        self.playerRoleTable.setObjectName("playerRoleAnalysisTable")
        self.playerRoleTable.setHorizontalHeaderLabels(
            ("Role", "Name", "Generic Role Fit", "Calculation breakdown")
        )
        self.playerRoleTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.playerRoleTable.setWordWrap(False)
        playerHeader = self.playerRoleTable.horizontalHeader()
        playerHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        playerHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        playerHeader.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        playerHeader.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.playerRoleTable.setMaximumHeight(190)

        if root is not None:
            root.addWidget(self.playerRoleTitle)
            playerControls = QHBoxLayout()
            playerLabel = QLabel("Player", self)
            playerLabel.setObjectName("eyebrow")
            playerControls.addWidget(playerLabel)
            playerControls.addWidget(self.playerPicker)
            playerControls.addStretch()
            root.addLayout(playerControls)
            root.addWidget(self.playerRoleTable)

        self.playerPicker.currentIndexChanged.connect(self._playerPickerChanged)
        self.candidateTable.cellClicked.connect(self._candidatePlayerSelect)
        self._allCandidatesShow()
        self._rowsCompact()

    def _roleShow(
        self,
        currentRow: int,
        currentColumn: int,
        previousRow: int,
        previousColumn: int,
    ) -> None:
        if not hasattr(self, "candidateTable"):
            return
        if currentRow < 0:
            self._allCandidatesShow()
            return
        roleItem = self.roleTable.item(currentRow, 0)
        role = (
            self.rolesByCode.get(str(roleItem.data(Qt.ItemDataRole.UserRole)))
            if roleItem is not None
            else None
        )
        if role is None:
            self._allCandidatesShow()
            return
        self._candidatesPopulate(
            tuple(
                candidate
                for candidate in role.candidates
                if _candidateEligible(role, candidate)
            )
        )

    def _selectionClear(self) -> None:
        self.roleTable.clearSelection()
        self.roleTable.setCurrentCell(-1, -1)
        self._allCandidatesShow()

    def _allCandidatesShow(self) -> None:
        """Default to one row per player using their best visible eligible role result."""

        best: dict[str, CandidateDisplay] = {}
        for role in self.roles:
            for candidate in role.candidates:
                if not _candidateEligible(role, candidate):
                    continue
                key = candidate.name.casefold()
                current = best.get(key)
                if current is None or (
                    candidate.available
                    and (
                        not current.available
                        or float(candidate.score) > float(current.score)
                    )
                ):
                    best[key] = candidate
        self._candidatesPopulate(
            tuple(sorted(best.values(), key=lambda candidate: candidate.name.casefold()))
        )

    def _candidatesPopulate(self, candidates: tuple[CandidateDisplay, ...]) -> None:
        self.candidateTable.setSortingEnabled(False)
        self.candidateTable.setRowCount(len(candidates))
        for row, candidate in enumerate(candidates):
            values = (
                candidate.name,
                candidate.positions,
                candidate.score,
                candidate.bestRole,
                _breakdownCompact(candidate.breakdown, self.attributes),
            )
            for column, value in enumerate(values):
                sortValue = (
                    float(candidate.score)
                    if column == 2 and candidate.available
                    else -1.0 if column == 2 else value.casefold()
                )
                item = SortableTableWidgetItem(value, sortValue)
                if column == 4:
                    item.setToolTip(candidate.breakdown)
                self.candidateTable.setItem(row, column, item)
        _columnsLeftAlign(self.candidateTable, (0, 1))
        self.candidateTable.setSortingEnabled(True)
        self._rowsCompact()

    def _allPlayerNames(self) -> set[str]:
        return {candidate.name for role in self.roles for candidate in role.candidates}

    def _candidatePlayerSelect(self, row: int, _column: int) -> None:
        item = self.candidateTable.item(row, 0)
        if item is not None:
            index = self.playerPicker.findData(item.text())
            if index >= 0:
                self.playerPicker.setCurrentIndex(index)

    def _playerPickerChanged(self, index: int) -> None:
        playerName = str(self.playerPicker.itemData(index) or "")
        self._playerRolesShow(playerName)

    def _playerRolesShow(self, playerName: str) -> None:
        rows = []
        if playerName:
            for role in self.roles:
                candidate = next(
                    (item for item in role.candidates if item.name == playerName),
                    None,
                )
                if candidate is not None and _candidateEligible(role, candidate):
                    rows.append((role, candidate))
        rows.sort(
            key=lambda item: (
                not item[1].available,
                -(float(item[1].score) if item[1].available else -1.0),
                item[0].displayName.casefold(),
            )
        )
        self.playerRoleTable.setRowCount(len(rows))
        for row, (role, candidate) in enumerate(rows):
            for column, value in enumerate(
                (
                    role.abbreviation,
                    role.displayName,
                    candidate.score,
                    candidate.breakdown,
                )
            ):
                self.playerRoleTable.setItem(row, column, QTableWidgetItem(value))
        _breakdownAbbreviate(self.playerRoleTable, 3, self.attributes)
        self._tooltipsApply(self.playerRoleTable, 3, preserve=True)
        for row in range(self.playerRoleTable.rowCount()):
            self.playerRoleTable.setRowHeight(row, 28)

    def _rowsCompact(self) -> None:
        for table in (self.roleTable, self.candidateTable):
            for row in range(table.rowCount()):
                table.setRowHeight(row, 28)

    @staticmethod
    def _tooltipsApply(
        table: QTableWidget,
        column: int,
        *,
        preserve: bool = False,
    ) -> None:
        for row in range(table.rowCount()):
            item = table.item(row, column)
            if item is not None and (not preserve or not item.toolTip()):
                item.setToolTip(item.text())


class SquadAnalysisTab(BaseSquadAnalysisTab):
    """Arrange depth and player strengths above full-width squad findings."""

    def __init__(
        self,
        model: SquadDetailModel,
        attributes: tuple[AttributeDefinition, ...] = (),
        requiredRows: tuple[tuple[str, str], ...] = (),
        parent=None,
    ) -> None:
        super().__init__(model, parent)
        self._depthExpand(model, requiredRows)
        for table in (self.depthTable, self.playerTable, self.findingsTable):
            self._compactTable(table)
        _breakdownAbbreviate(self.playerTable, 3, attributes)
        _columnsLeftAlign(self.playerTable, (0,))
        self._tooltipsApply(self.playerTable, 3, preserve=True)
        self._tooltipsApply(self.findingsTable, 2)
        self._dashboardArrange()
        self._rowsCompact()

    def _depthExpand(
        self,
        model: SquadDetailModel,
        requiredRows: tuple[tuple[str, str], ...],
    ) -> None:
        rows = list(requiredRows)
        if not rows:
            for role in model.roles:
                positions = tuple(
                    value.strip() for value in role.positions.split(",") if value.strip()
                ) or ("",)
                for position in positions:
                    label = (
                        role.abbreviation
                        + (f" · {position}" if position else "")
                        + f" — {role.displayName}"
                    )
                    rows.append((label, role.coverage))
        self.depthTable.setRowCount(len(rows))
        for row, (label, coverage) in enumerate(rows):
            self.depthTable.setItem(row, 0, QTableWidgetItem(label))
            self.depthTable.setItem(row, 1, QTableWidgetItem(coverage))

    @staticmethod
    def _compactTable(table: QTableWidget) -> None:
        table.setWordWrap(False)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _dashboardArrange(self) -> None:
        root = self.layout()
        if root is None:
            return
        context = root.itemAt(0).widget() if root.count() else None
        while root.count():
            item = root.takeAt(0)
            widget = item.widget()
            if (
                widget is not None
                and widget is not context
                and widget
                not in {self.depthTable, self.playerTable, self.findingsTable}
            ):
                widget.deleteLater()
        if context is not None:
            context.setParent(self)
            root.addWidget(context)
        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(self._cardCreate("Required Role Depth", self.depthTable), 2)
        top.addWidget(self._cardCreate("Player Role Strengths", self.playerTable), 3)
        root.addLayout(top, 3)
        root.addWidget(self._cardCreate("Squad Depth Findings", self.findingsTable), 2)

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
    def _tooltipsApply(
        table: QTableWidget,
        column: int,
        *,
        preserve: bool = False,
    ) -> None:
        for row in range(table.rowCount()):
            item = table.item(row, column)
            if item is not None and (not preserve or not item.toolTip()):
                item.setToolTip(item.text())
