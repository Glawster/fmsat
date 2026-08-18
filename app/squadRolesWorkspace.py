"""Role browsing workspace with tactic roles beside stacked player evidence."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.presentation import playerNameSortKey
from fmsat.app.squadDetailModel import CandidateDisplay, RoleDisplay
from fmsat.app.squadDetailTabOverrides import (
    _breakdownAbbreviate,
    _breakdownCompact,
    _candidateEligible,
    _columnsLeftAlign,
)
from fmsat.app.squadDetailTabs import SortableTableWidgetItem, SquadRolesTab as BaseSquadRolesTab
from fmsat.core.config import AttributeDefinition


class SquadRolesTab(BaseSquadRolesTab):
    """Show tactic roles full-height with candidate and player-role panes on the right."""

    def __init__(
        self,
        roles: tuple[RoleDisplay, ...],
        attributes: tuple[AttributeDefinition, ...] = (),
        parent: QWidget | None = None,
    ) -> None:
        # Build the base tables first so their shared palette and role metadata stay reused.
        self.attributes = attributes
        self.roleSortOrder = Qt.SortOrder.AscendingOrder
        super().__init__(roles, parent)
        if not hasattr(self, "candidateTable"):
            return

        self.roleTable.clearSelection()
        self.roleTable.setCurrentCell(-1, -1)
        self._roleTableRebuild()
        self._candidateTablePrepare()
        self._playerRolePaneCreate()
        self._workspaceRebuild()

        self.playerPicker.currentIndexChanged.connect(self._playerPickerChanged)
        self.candidateTable.cellClicked.connect(self._candidatePlayerSelect)
        self._allCandidatesShow()
        self._rowsCompact()

    def _roleTableRebuild(self) -> None:
        """Use role abbreviation and compact eligible depth, retaining roleCode metadata."""

        self.roleTable.setSortingEnabled(False)
        self.roleTable.setColumnCount(2)
        self.roleTable.setHorizontalHeaderLabels(("Role", "Coverage"))
        self.roleTable.setRowCount(len(self.roles))
        for row, role in enumerate(self.roles):
            abbreviation = QTableWidgetItem(role.abbreviation)
            abbreviation.setData(Qt.ItemDataRole.UserRole, role.roleCode)
            abbreviation.setToolTip(role.displayName)
            self.roleTable.setItem(row, 0, abbreviation)

            coverageText = self._roleCoverageRender(role)
            coverage = QTableWidgetItem(coverageText)
            coverage.setToolTip(coverageText)
            self.roleTable.setItem(row, 1, coverage)

        header = self.roleTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._roleHeaderClicked)
        self.roleTable.setMinimumWidth(300)
        self.roleTable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.roleTable.verticalHeader().setDefaultSectionSize(28)

    @staticmethod
    def _roleCoverageCandidates(role: RoleDisplay) -> tuple[CandidateDisplay, ...]:
        """Return the top position-eligible calculable candidates shown as role depth."""

        eligible = tuple(
            candidate
            for candidate in role.candidates
            if candidate.available and _candidateEligible(role, candidate)
        )
        return tuple(
            sorted(
                eligible,
                key=lambda candidate: (
                    -float(candidate.score),
                    playerNameSortKey(candidate.name),
                ),
            )[:2]
        )

    @classmethod
    def _roleCoverageRender(cls, role: RoleDisplay) -> str:
        """Render best-first depth without repetitive Best/Backup labels."""

        candidates = cls._roleCoverageCandidates(role)
        if not candidates:
            hasEligible = any(_candidateEligible(role, candidate) for candidate in role.candidates)
            return "Unavailable" if hasEligible else "Uncovered"
        return " · ".join(candidate.name for candidate in candidates)

    def _roleHeaderClicked(self, column: int) -> None:
        """Sort alphabetically only when the user explicitly clicks the Role header."""

        if column != 0:
            return
        self.roleTable.sortItems(0, self.roleSortOrder)
        self.roleSortOrder = (
            Qt.SortOrder.DescendingOrder
            if self.roleSortOrder is Qt.SortOrder.AscendingOrder
            else Qt.SortOrder.AscendingOrder
        )

    def _candidateTablePrepare(self) -> None:
        self.candidateTable.setWordWrap(False)
        self.candidateTable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.candidateTable.verticalHeader().setDefaultSectionSize(28)

    def _playerRolePaneCreate(self) -> None:
        self.playerRoleTitle = QLabel("Player Role Assessment", self)
        self.playerRoleTitle.setObjectName("workspaceHeading")
        self.playerPicker = QComboBox(self)
        self.playerPicker.setObjectName("rolePlayerPicker")
        self.playerPicker.setMaximumWidth(320)
        self.playerPicker.addItem("Select a player…", "")
        for name in sorted(self._allPlayerNames(), key=playerNameSortKey):
            self.playerPicker.addItem(name, name)

        self.playerRoleTable = QTableWidget(0, 4, self)
        self.playerRoleTable.setObjectName("playerRoleAnalysisTable")
        self.playerRoleTable.setHorizontalHeaderLabels(
            ("Role", "Name", "Generic Role Fit", "Calculation breakdown")
        )
        self.playerRoleTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.playerRoleTable.setWordWrap(False)
        header = self.playerRoleTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

    def _workspaceRebuild(self) -> None:
        """Replace the base horizontal table strip with the requested two-column workspace."""

        root = self.layout()
        if root is None:
            return
        oldSplitter = self.roleTable.parentWidget()
        while root.count():
            root.takeAt(0)

        self.clearRoleButton = QPushButton("Show all players / roles", self)
        self.clearRoleButton.setObjectName("secondaryButton")
        self.clearRoleButton.clicked.connect(self._selectionClear)
        root.addWidget(self.clearRoleButton, 0, Qt.AlignmentFlag.AlignLeft)

        mainSplitter = QSplitter(Qt.Orientation.Horizontal, self)
        mainSplitter.setObjectName("roleWorkspaceSplitter")

        leftPane = QWidget(mainSplitter)
        leftLayout = QVBoxLayout(leftPane)
        leftLayout.setContentsMargins(0, 0, 0, 0)
        self.rolePaneTitle = QLabel("Tactic Roles", leftPane)
        self.rolePaneTitle.setObjectName("workspaceHeading")
        leftLayout.addWidget(self.rolePaneTitle)
        self.roleTable.setParent(leftPane)
        leftLayout.addWidget(self.roleTable, 1)

        rightSplitter = QSplitter(Qt.Orientation.Vertical, mainSplitter)
        rightSplitter.setObjectName("roleEvidenceSplitter")

        candidatePane = QWidget(rightSplitter)
        candidateLayout = QVBoxLayout(candidatePane)
        candidateLayout.setContentsMargins(0, 0, 0, 0)
        self.candidatePaneTitle = QLabel("Candidates for Selected Role", candidatePane)
        self.candidatePaneTitle.setObjectName("workspaceHeading")
        candidateLayout.addWidget(self.candidatePaneTitle)
        self.candidateTable.setParent(candidatePane)
        candidateLayout.addWidget(self.candidateTable, 1)

        playerPane = QWidget(rightSplitter)
        playerLayout = QVBoxLayout(playerPane)
        playerLayout.setContentsMargins(0, 0, 0, 0)
        self.playerRoleTitle.setParent(playerPane)
        playerLayout.addWidget(self.playerRoleTitle)
        controls = QHBoxLayout()
        playerLabel = QLabel("Player", playerPane)
        playerLabel.setObjectName("eyebrow")
        controls.addWidget(playerLabel)
        self.playerPicker.setParent(playerPane)
        controls.addWidget(self.playerPicker)
        controls.addStretch()
        playerLayout.addLayout(controls)
        self.playerRoleTable.setParent(playerPane)
        playerLayout.addWidget(self.playerRoleTable, 1)

        rightSplitter.addWidget(candidatePane)
        rightSplitter.addWidget(playerPane)
        rightSplitter.setStretchFactor(0, 3)
        rightSplitter.setStretchFactor(1, 2)
        rightSplitter.setSizes([430, 280])

        mainSplitter.addWidget(leftPane)
        mainSplitter.addWidget(rightSplitter)
        mainSplitter.setStretchFactor(0, 1)
        mainSplitter.setStretchFactor(1, 4)
        mainSplitter.setSizes([330, 1120])
        root.addWidget(mainSplitter, 1)

        if oldSplitter is not None and oldSplitter is not mainSplitter:
            oldSplitter.deleteLater()

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
            tuple(sorted(best.values(), key=lambda candidate: playerNameSortKey(candidate.name)))
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
        self._playerRolesShow(str(self.playerPicker.itemData(index) or ""))

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
