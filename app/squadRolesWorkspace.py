"""Role browsing workspace with tactic roles beside stacked player evidence."""

from __future__ import annotations

import re

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

from fmsat.app.presentation import playerNameSortKey, playerSurnameDisplay
from fmsat.app.squadDetailModel import CandidateDisplay, RoleDisplay
from fmsat.app.squadDetailTabOverrides import _candidateEligible, _columnsLeftAlign
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
        self.attributes = attributes
        self.roleSortOrder = Qt.SortOrder.AscendingOrder
        self.candidateRoleSortInitialized = False
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
        self.roleTable.cellDoubleClicked.connect(self._roleEditRequested)
        self._allCandidatesShow()
        self._rowsCompact()

    def _roleTableRebuild(self) -> None:
        self.roleTable.setSortingEnabled(False)
        self.roleTable.setColumnCount(3)
        self.roleTable.setHorizontalHeaderLabels(("IP", "OOP", "Coverage"))
        self.roleTable.setRowCount(len(self.roles))
        for row, role in enumerate(self.roles):
            ipText, oopText = self._rolePhaseCells(role)
            tooltip = self._roleTooltip(role)
            for column, text in enumerate((ipText, oopText)):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, role.roleCode)
                item.setToolTip(tooltip if text else role.displayName)
                self.roleTable.setItem(row, column, item)
            coverageText = self._roleCoverageRender(role)
            coverage = QTableWidgetItem(coverageText)
            coverage.setToolTip(role.resolutionReason or coverageText)
            self.roleTable.setItem(row, 2, coverage)
        header = self.roleTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._roleHeaderClicked)
        self.roleTable.setMinimumWidth(370)
        self.roleTable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.roleTable.verticalHeader().setDefaultSectionSize(28)

    @classmethod
    def _rolePhaseCells(cls, role: RoleDisplay) -> tuple[str, str]:
        phases = {phase.strip().casefold() for phase in role.phases.split(",")}
        inPossession = any(phase in {"ip", "in possession"} for phase in phases)
        outOfPossession = any(phase in {"oop", "out of possession"} for phase in phases)
        label = cls._roleLabel(role)
        return (label if inPossession else "", label if outOfPossession else "")

    @staticmethod
    def _roleLabel(role: RoleDisplay) -> str:
        if role.resolutionState == "unknownRole":
            observed = role.abbreviation.strip()
            return observed if observed and observed != "Unknown" else "Unknown role"
        if role.resolutionState == "missingAbbreviation":
            return "Unknown abbreviation"
        return role.abbreviation

    @staticmethod
    def _roleTooltip(role: RoleDisplay) -> str:
        if role.resolutionState == "unknownRole":
            return f"{role.displayName} ({role.roleCode}) has no confirmed role definition. Double-click to resolve it in the Role Editor."
        if role.resolutionState == "missingAbbreviation":
            return f"{role.displayName} has no confirmed abbreviation. Double-click to update it in the Role Editor."
        if role.resolutionState == "missingWeights":
            return f"{role.displayName}: assessment weights are not defined. Double-click to update them in the Role Editor."
        return f"{role.displayName}. Double-click to open the Role Editor."

    @staticmethod
    def _roleCoverageCandidates(role: RoleDisplay) -> tuple[CandidateDisplay, ...]:
        eligible = tuple(
            candidate
            for candidate in role.candidates
            if candidate.available and _candidateEligible(role, candidate)
        )
        return tuple(
            sorted(
                eligible,
                key=lambda candidate: (-float(candidate.score), playerNameSortKey(candidate.name)),
            )[:2]
        )

    @classmethod
    def _roleCoverageRender(cls, role: RoleDisplay) -> str:
        candidates = cls._roleCoverageCandidates(role)
        if not candidates:
            return "No Candidates found"
        return " - ".join(playerSurnameDisplay(candidate.name) for candidate in candidates)

    def _roleHeaderClicked(self, column: int) -> None:
        if column not in (0, 1):
            return
        self.roleTable.sortItems(column, self.roleSortOrder)
        self.roleSortOrder = (
            Qt.SortOrder.DescendingOrder
            if self.roleSortOrder is Qt.SortOrder.AscendingOrder
            else Qt.SortOrder.AscendingOrder
        )

    def _roleEditRequested(self, row: int, column: int) -> None:
        if column not in (0, 1):
            return
        item = self.roleTable.item(row, column)
        if item is None or not item.text():
            return
        roleCode = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not roleCode:
            return
        window = self.window()
        knowledge = getattr(window, "roleKnowledgeService", None)
        roleShow = getattr(window, "roleShow", None)
        if (
            knowledge is not None
            and callable(getattr(knowledge, "definitionExists", None))
            and knowledge.definitionExists(roleCode)
            and callable(roleShow)
        ):
            roleShow(roleCode)
            return
        roleImport = getattr(window, "roleProfileImport", None)
        if callable(roleImport):
            roleImport()

    def _unknownRoleEdit(self, row: int, column: int) -> None:
        self._roleEditRequested(row, column)

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
        self.playerRoleTable = QTableWidget(0, 3, self)
        self.playerRoleTable.setObjectName("playerRoleAnalysisTable")
        self.playerRoleTable.setHorizontalHeaderLabels(("Role", "Name", "Generic Role Fit"))
        self.playerRoleTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.playerRoleTable.setWordWrap(False)
        header = self.playerRoleTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

    def _workspaceRebuild(self) -> None:
        root = self.layout()
        if root is None:
            return
        oldSplitter = self.roleTable.parentWidget()
        while root.count():
            root.takeAt(0)
        workspaceControls = QHBoxLayout()
        self.clearRoleButton = QPushButton("Show all players / roles", self)
        self.clearRoleButton.setObjectName("secondaryButton")
        self.clearRoleButton.clicked.connect(self._selectionClear)
        workspaceControls.addWidget(self.clearRoleButton)
        workspaceControls.addStretch()
        self.reassessButton = QPushButton("Reassess Squad", self)
        self.reassessButton.setObjectName("secondaryButton")
        self.reassessButton.setToolTip(
            "Recalculate role fit and squad analysis from saved player evidence without running OCR."
        )
        self.reassessButton.clicked.connect(self._reassessRequest)
        workspaceControls.addWidget(self.reassessButton)
        root.addLayout(workspaceControls)
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
        mainSplitter.setSizes([400, 1050])
        root.addWidget(mainSplitter, 1)
        if oldSplitter is not None and oldSplitter is not mainSplitter:
            oldSplitter.deleteLater()

    def _reassessRequest(self) -> None:
        owner = self.parentWidget()
        while owner is not None:
            reassess = getattr(owner, "_reassessRequest", None)
            if callable(reassess):
                reassess()
                return
            owner = owner.parentWidget()

    def _roleShow(
        self, currentRow: int, currentColumn: int, previousRow: int, previousColumn: int
    ) -> None:
        if not hasattr(self, "candidateTable"):
            return
        if currentRow < 0:
            self._allCandidatesShow()
            return
        roleItem = self.roleTable.item(currentRow, currentColumn)
        if roleItem is None or currentColumn == 2:
            roleItem = self.roleTable.item(currentRow, 0) or self.roleTable.item(currentRow, 1)
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
                candidate for candidate in role.candidates if _candidateEligible(role, candidate)
            ),
            role,
        )

    def _selectionClear(self) -> None:
        self.roleTable.clearSelection()
        self.roleTable.setCurrentCell(-1, -1)
        self._allCandidatesShow()

    def _allCandidatesShow(self) -> None:
        best: dict[str, CandidateDisplay] = {}
        for role in self.roles:
            for candidate in role.candidates:
                if not _candidateEligible(role, candidate):
                    continue
                key = candidate.name.casefold()
                current = best.get(key)
                if current is None or (
                    candidate.available
                    and (not current.available or float(candidate.score) > float(current.score))
                ):
                    best[key] = candidate
        self._candidatesPopulate(
            tuple(sorted(best.values(), key=lambda candidate: playerNameSortKey(candidate.name)))
        )

    def _attributeDefinition(self, name: str) -> AttributeDefinition | None:
        folded = name.strip().casefold()
        return next(
            (attribute for attribute in self.attributes if attribute.name.casefold() == folded),
            None,
        )

    @staticmethod
    def _candidateAttributeValues(candidate: CandidateDisplay) -> dict[str, str]:
        """Read raw player values from the retained Generic Role Fit contribution evidence."""
        values: dict[str, str] = {}
        for component in candidate.breakdown.split(";"):
            match = re.match(r"\s*([^:]+):\s*([^×]+?)\s*×", component)
            if match is not None:
                name, value = match.groups()
                values[name.strip()] = value.strip()
        return values

    def _attributeNamesOrder(self, present: set[str]) -> tuple[str, ...]:
        """Keep dynamic attribute columns in configured FM order, then stable unknown order."""
        configured = [attribute.name for attribute in self.attributes if attribute.name in present]
        configuredSet = set(configured)
        return tuple(configured + sorted(present - configuredSet, key=str.casefold))

    def _selectedRoleAttributes(self, candidates: tuple[CandidateDisplay, ...]) -> tuple[str, ...]:
        present = {
            name for candidate in candidates for name in self._candidateAttributeValues(candidate)
        }
        return self._attributeNamesOrder(present)

    def _candidatesPopulate(
        self, candidates: tuple[CandidateDisplay, ...], role: RoleDisplay | None = None
    ) -> None:
        self.candidateTable.setSortingEnabled(False)
        attributeNames = self._selectedRoleAttributes(candidates) if role is not None else ()
        headers = ["Player", "Natural positions", "Generic Role Fit", "Best role"]
        if role is not None:
            for name in attributeNames:
                definition = self._attributeDefinition(name)
                headers.append(
                    definition.abbreviation
                    if definition and definition.abbreviation.strip()
                    else name
                )
        self.candidateTable.clearContents()
        self.candidateTable.setColumnCount(len(headers))
        self.candidateTable.setHorizontalHeaderLabels(headers)
        self.candidateTable.setRowCount(len(candidates))
        for offset, name in enumerate(attributeNames, start=4):
            definition = self._attributeDefinition(name)
            headerItem = self.candidateTable.horizontalHeaderItem(offset)
            if headerItem is not None:
                headerItem.setToolTip(definition.name if definition is not None else name)
        for row, candidate in enumerate(candidates):
            attributeValues = self._candidateAttributeValues(candidate)
            values = [candidate.name, candidate.positions, candidate.score, candidate.bestRole]
            values.extend(attributeValues.get(name, "—") for name in attributeNames)
            for column, value in enumerate(values):
                if column == 2:
                    sortValue = float(candidate.score) if candidate.available else -1.0
                elif role is not None and column >= 4:
                    try:
                        sortValue = float(value)
                    except ValueError:
                        sortValue = -1.0
                else:
                    sortValue = value.casefold()
                item = SortableTableWidgetItem(value, sortValue)
                self.candidateTable.setItem(row, column, item)
        _columnsLeftAlign(self.candidateTable, (0, 1))
        header = self.candidateTable.horizontalHeader()
        for column in range(self.candidateTable.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        if self.candidateTable.columnCount() >= 4:
            header.setSectionResizeMode(
                self.candidateTable.columnCount() - 1,
                QHeaderView.ResizeMode.Stretch,
            )
        self.candidateTable.setSortingEnabled(True)
        if role is not None and not self.candidateRoleSortInitialized:
            self.candidateTable.sortItems(2, Qt.SortOrder.DescendingOrder)
            self.candidateRoleSortInitialized = True
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
        rows: list[tuple[RoleDisplay, CandidateDisplay]] = []
        if playerName:
            for role in self.roles:
                candidate = next(
                    (item for item in role.candidates if item.name == playerName), None
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

        # Each row can represent a different role, so use the ordered union of every
        # attribute required by the currently visible role assessments.
        attributeValuesByRow = [
            self._candidateAttributeValues(candidate) for _role, candidate in rows
        ]
        attributeNames = self._attributeNamesOrder(
            {name for values in attributeValuesByRow for name in values}
        )
        headers = ["Role", "Name", "Generic Role Fit"]
        for name in attributeNames:
            definition = self._attributeDefinition(name)
            headers.append(
                definition.abbreviation if definition and definition.abbreviation.strip() else name
            )

        self.playerRoleTable.setSortingEnabled(False)
        self.playerRoleTable.clearContents()
        self.playerRoleTable.setColumnCount(len(headers))
        self.playerRoleTable.setHorizontalHeaderLabels(headers)
        self.playerRoleTable.setRowCount(len(rows))
        for offset, name in enumerate(attributeNames, start=3):
            definition = self._attributeDefinition(name)
            headerItem = self.playerRoleTable.horizontalHeaderItem(offset)
            if headerItem is not None:
                headerItem.setToolTip(definition.name if definition is not None else name)

        for row, ((role, candidate), attributeValues) in enumerate(zip(rows, attributeValuesByRow)):
            values = [self._roleLabel(role), role.displayName, candidate.score]
            values.extend(attributeValues.get(name, "—") for name in attributeNames)
            for column, value in enumerate(values):
                if column == 2:
                    sortValue = float(candidate.score) if candidate.available else -1.0
                elif column >= 3:
                    try:
                        sortValue = float(value)
                    except ValueError:
                        sortValue = -1.0
                else:
                    sortValue = value.casefold()
                self.playerRoleTable.setItem(row, column, SortableTableWidgetItem(value, sortValue))
            self.playerRoleTable.setRowHeight(row, 28)

        header = self.playerRoleTable.horizontalHeader()
        for column in range(self.playerRoleTable.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.playerRoleTable.setSortingEnabled(True)

    def _rowsCompact(self) -> None:
        for table in (self.roleTable, self.candidateTable):
            for row in range(table.rowCount()):
                table.setRowHeight(row, 28)

    @staticmethod
    def _tooltipsApply(table: QTableWidget, column: int, *, preserve: bool = False) -> None:
        for row in range(table.rowCount()):
            item = table.item(row, column)
            if item is not None and (not preserve or not item.toolTip()):
                item.setToolTip(item.text())
