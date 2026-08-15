"""Tab widgets composed by the squad detail workspace."""

from __future__ import annotations

import re

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QHeaderView,
    QLineEdit,
    QMenu,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from fmsat.app.squadDetailModel import RoleDisplay, SquadDetailModel
from fmsat.core.config import AttributeDefinition
from fmsat.core.squadModel import SquadModel, SquadModelPlayer
from fmsat.football.trait import playerTraits


class PlayerTraitDialog(QDialog):
    """Select a player's known traits from the canonical FM26 catalogue."""

    commonTraits = frozenset(
        {
            "Moves Into Channels",
            "Gets Forward Whenever Possible",
            "Plays Short Simple Passes",
            "Tries Killer Balls Often",
            "Places Shots",
            "Tries To Play Way Out Of Trouble",
            "Stays Back At All Times",
            "Comes Deep To Get Ball",
            "Hugs Line",
            "Marks Opponent Tightly",
            "Plays One-Twos",
            "Dictates Tempo",
            "Tries Long Range Passes",
            "Likes To Switch Ball To Wide Areas",
            "Bring Ball Out of Defence",
        }
    )
    categoryOrder = (
        "Commonly Used",
        "Movement",
        "Passing & Creativity",
        "Shooting",
        "Defending",
        "Dribbling & Technique",
        "Set Pieces",
        "Goalkeeping",
        "Behaviour & Decisions",
    )

    def __init__(
        self,
        selected: tuple[str, ...],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Known Traits")
        self.resize(560, 620)
        layout = QVBoxLayout(self)
        prompt = QLabel("Select every trait known to be set for this player.")
        prompt.setObjectName("mutedText")
        layout.addWidget(prompt)
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Filter traits…")
        layout.addWidget(self.search)
        self.selectedOnly = QCheckBox("Show selected traits only", self)
        layout.addWidget(self.selectedOnly)
        self.tree = QTreeWidget(self)
        self.tree.setObjectName("playerTraitList")
        self.tree.setHeaderHidden(True)
        selectedNames = set(selected)
        canonicalNames = [trait.name for trait in playerTraits]
        names = canonicalNames + sorted(selectedNames.difference(canonicalNames), key=str.casefold)
        categories = {
            category: QTreeWidgetItem(self.tree, (category,))
            for category in self.categoryOrder
        }
        for parentItem in categories.values():
            parentItem.setFlags(parentItem.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        for name in names:
            category = self._traitCategory(name)
            parentItem = categories[category]
            item = QTreeWidgetItem(parentItem, (name,))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                0,
                Qt.CheckState.Checked if name in selectedNames else Qt.CheckState.Unchecked,
            )
        self.tree.expandAll()
        layout.addWidget(self.tree, 1)
        self.summary = QLabel()
        self.summary.setObjectName("mutedText")
        layout.addWidget(self.summary)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.search.textChanged.connect(lambda _text: self._filterApply())
        self.selectedOnly.toggled.connect(lambda _checked: self._filterApply())
        self.tree.itemChanged.connect(lambda _item, _column: self._selectionChange())
        self._summaryUpdate()

    def selectedTraits(self) -> tuple[str, ...]:
        """Return checked traits in stable catalogue order."""

        return tuple(
            parent.child(row).text(0)
            for parentIndex in range(self.tree.topLevelItemCount())
            for parent in (self.tree.topLevelItem(parentIndex),)
            for row in range(parent.childCount())
            if parent.child(row).checkState(0) is Qt.CheckState.Checked
        )

    def _filterApply(self) -> None:
        query = self.search.text().strip().casefold()
        for parentIndex in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(parentIndex)
            visibleChildren = 0
            for row in range(parent.childCount()):
                item = parent.child(row)
                hidden = bool(query and query not in item.text(0).casefold()) or (
                    self.selectedOnly.isChecked()
                    and item.checkState(0) is not Qt.CheckState.Checked
                )
                item.setHidden(hidden)
                visibleChildren += not hidden
            parent.setHidden(visibleChildren == 0)

    def _selectionChange(self) -> None:
        self._summaryUpdate()
        if self.selectedOnly.isChecked():
            self._filterApply()

    def _summaryUpdate(self) -> None:
        count = len(self.selectedTraits())
        self.summary.setText(f"{count} trait{'s' if count != 1 else ''} selected")

    @staticmethod
    def _traitCategory(name: str) -> str:
        """Place the large FM trait catalogue into small browsing groups."""

        if name in PlayerTraitDialog.commonTraits:
            return "Commonly Used"
        lowered = name.casefold()
        if any(token in lowered for token in ("keeper", "plays ball with feet")):
            return "Goalkeeping"
        if any(
            token in lowered
            for token in ("free kick", "penalt", "long flat throw", "long throw")
        ):
            return "Set Pieces"
        if any(
            token in lowered
            for token in ("shoot", "score", "overhead", "penalty box", "places shots")
        ):
            return "Shooting"
        if any(token in lowered for token in ("tackle", "marks opponent", "stays back")):
            return "Defending"
        if any(
            token in lowered
            for token in (
                "knocks ball",
                "weaker foot",
                "outside of foot",
                "tries tricks",
                "beat opponent",
                "before dribble",
                "runs with ball often",
                "runs with ball rarely",
            )
        ):
            return "Dribbling & Technique"
        if any(
            token in lowered
            for token in ("pass", "through balls", "one-twos", "tempo", "crosses early")
        ):
            return "Passing & Creativity"
        if any(
            token in lowered
            for token in (
                "runs with ball",
                "gets into",
                "moves into",
                "gets forward",
                "offside trap",
                "arrives late",
                "comes deep",
                "hugs line",
                "cuts inside",
            )
        ):
            return "Movement"
        return "Behaviour & Decisions"


class SquadAnalysisTab(QWidget):
    """Explain that later assessment stages have not been generated yet."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addStretch()
        title = QLabel("Further Squad Analysis Is Not Generated Yet")
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        copy = QLabel(
            "Generic Role Fit and initial role coverage are available in Roles. "
            "Tactical Fit, Overall Suitability, Best XI and recruitment analysis "
            "will be added as separate explainable calculations."
        )
        copy.setObjectName("mutedText")
        copy.setWordWrap(True)
        copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copy)
        layout.addStretch()


class SquadOverviewTab(QWidget):
    """Summarize model provenance and initial role coverage."""

    def __init__(self, model: SquadDetailModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.addWidget(
            self._panel(
                "Squad Model",
                (
                    ("Players", str(len(model.squad.players))),
                    ("Tactic", model.tacticName),
                    ("Updated", model.updated),
                    ("Source", model.sourceStatus),
                ),
            ),
            1,
        )
        covered = sum(not role.coverage.startswith("Uncovered") for role in model.roles)
        layout.addWidget(
            self._panel(
                "Role Coverage",
                (
                    ("Required positions", str(model.requiredPositionCount)),
                    ("Unique tactic roles", str(len(model.roles))),
                    ("Covered unique roles", str(covered)),
                    ("Uncovered unique roles", str(len(model.roles) - covered)),
                    (
                        "Scoring stage",
                        "Generic Role Fit only; position is context, not the assessment identity",
                    ),
                ),
            ),
            1,
        )

    @staticmethod
    def _panel(title: str, values: tuple[tuple[str, str], ...]) -> QFrame:
        panel = QFrame()
        panel.setObjectName("overviewPanel")
        layout = QVBoxLayout(panel)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        layout.addWidget(heading)
        for label, value in values:
            key = QLabel(label)
            key.setObjectName("overviewFieldKey")
            layout.addWidget(key)
            fieldValue = QLabel(value)
            fieldValue.setObjectName("overviewFieldValue")
            fieldValue.setWordWrap(True)
            layout.addWidget(fieldValue)
        layout.addStretch()
        return panel


class SquadPlayersTab(QWidget):
    """Display and edit the current squad model rather than screenshot rows."""

    changed = Signal()
    goalkeeperAttributeNames = frozenset(
        {
            "aerial_reach",
            "command_of_area",
            "communication",
            "eccentricity",
            "handling",
            "kicking",
            "one_on_ones",
            "punching",
            "reflexes",
            "rushing_out",
            "tendency_to_punch",
            "throwing",
        }
    )

    def __init__(
        self,
        model: SquadModel,
        attributes: tuple[AttributeDefinition, ...] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        observedNames = {
            name for player in model.players for name, _value in player.attributes
        }
        configuredNames = tuple(attribute.name for attribute in attributes)
        self.attributeNames = configuredNames + tuple(
            sorted(observedNames.difference(configuredNames))
        )
        abbreviations = {
            attribute.name: attribute.abbreviation for attribute in attributes
        }
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        hint = QLabel(
            "Edit model values here. Saving preserves the screenshots as history and marks "
            "their evidence as superseded by this model. Attribute values must be 1–20."
        )
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)
        controls.addWidget(hint, 1)
        self.filterButton = self._filterCreate()
        controls.addWidget(self.filterButton)
        layout.addLayout(controls)
        headers = (
            "Name",
            "Positions",
            "CA",
            "PA",
            *(abbreviations.get(name, name) for name in self.attributeNames),
            "Known Traits",
        )
        self.table = QTableWidget(len(model.players), len(headers), self)
        self.table.setObjectName("squadPlayersTable")
        self.table.setHorizontalHeaderLabels(headers)
        for offset, attribute in enumerate(self.attributeNames, start=4):
            self.table.horizontalHeaderItem(offset).setToolTip(
                attribute.replace("_", " ").title()
            )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setSortingEnabled(False)
        for row, player in enumerate(model.players):
            values = dict(player.attributes)
            for column, value in enumerate(
                (player.name, player.positions, player.ca, player.pa)
            ):
                item = QTableWidgetItem(value)
                if column == 0:
                    # Sorting changes visual row order, so retain the source model identity.
                    item.setData(Qt.ItemDataRole.UserRole, row)
                self.table.setItem(row, column, item)
            for offset, attribute in enumerate(self.attributeNames, start=4):
                value = values.get(attribute)
                self.table.setItem(
                    row,
                    offset,
                    SortableTableWidgetItem(
                        "" if value is None else str(value),
                        value if value is not None else -1,
                    ),
                )
            traitsColumn = len(headers) - 1
            traitItem = QTableWidgetItem(", ".join(player.traits))
            traitItem.setFlags(traitItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, traitsColumn, traitItem)
            for column in range(len(headers)):
                item = self.table.item(row, column)
                if item is not None:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.item(row, traitsColumn).setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.item(row, traitsColumn).setToolTip("Click to edit known traits")
        # Attribute abbreviations make a compact, regular comparison grid possible.
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        for column in range(4, len(headers)):
            if column == len(headers) - 1:
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
                continue
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(column, 52)
        self.table.setSortingEnabled(True)
        self.table.itemChanged.connect(lambda _item: self.changed.emit())
        self.table.cellClicked.connect(self._traitEditorOpen)
        self._goalkeeperColumnsUpdate()
        layout.addWidget(self.table)

    def modelBuild(self) -> SquadModel:
        """Return validated edited values while retaining source provenance."""

        players = []
        for row in range(self.table.rowCount()):
            sourceIndex = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            original = self.model.players[int(sourceIndex)]
            attributes = []
            for column, attribute in enumerate(self.attributeNames, start=4):
                text = self._text(row, column)
                if not text:
                    value = None
                else:
                    value = int(text)
                    if not 1 <= value <= 20:
                        raise ValueError(f"{attribute} for row {row + 1} must be between 1 and 20")
                attributes.append((attribute, value))
            traits = tuple(
                dict.fromkeys(
                    value.strip()
                    for value in self._text(row, self.table.columnCount() - 1).split(",")
                    if value.strip()
                )
            )
            name = self._text(row, 0)
            if not name:
                raise ValueError(f"Player row {row + 1} requires a name")
            players.append(
                SquadModelPlayer(
                    name=name,
                    positions=self._text(row, 1),
                    ca=self._text(row, 2),
                    pa=self._text(row, 3),
                    confidence=original.confidence,
                    sourceImportSessionId=original.sourceImportSessionId,
                    validationState="corrected",
                    attributes=tuple(attributes),
                    traits=traits,
                )
            )
        return SquadModel(
            name=self.model.name,
            players=tuple(players),
            generatedAt=self.model.generatedAt,
            updatedAt=self.model.updatedAt,
            evidenceSuperseded=True,
            regenerationRequired=False,
        )

    def _text(self, row: int, column: int) -> str:
        item = self.table.item(row, column)
        return item.text().strip() if item is not None else ""

    ## filtering

    def _filterCreate(self) -> QToolButton:
        """Build the persistent position-unit checklist used to filter player rows."""

        button = QToolButton(self)
        button.setObjectName("playerFilterButton")
        button.setText("Filter · All Positions")
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(button)
        menu.setObjectName("playerFilterMenu")
        button.setMenu(menu)
        self.positionFilters: dict[str, QCheckBox] = {}
        for key, label in (
            ("all", "All Positions"),
            ("goalkeepers", "Goalkeepers"),
            ("defenders", "Defenders"),
            ("defensiveMidfielders", "Def. Midfielders"),
            ("midfielders", "Midfielders"),
            ("attackingMidfielders", "Att. Midfielders"),
            ("attackers", "Attackers"),
        ):
            checkbox = QCheckBox(label, menu)
            checkbox.setChecked(True)
            action = QWidgetAction(menu)
            action.setDefaultWidget(checkbox)
            menu.addAction(action)
            self.positionFilters[key] = checkbox
        self.positionFilters["all"].toggled.connect(self._allPositionsToggle)
        for key, checkbox in self.positionFilters.items():
            if key != "all":
                checkbox.toggled.connect(self._positionFilterApply)
        return button

    def _allPositionsToggle(self, checked: bool) -> None:
        for key, checkbox in self.positionFilters.items():
            if key == "all":
                continue
            blocker = QSignalBlocker(checkbox)
            checkbox.setChecked(checked)
            del blocker
        self._positionFilterApply()

    def _positionFilterApply(self) -> None:
        selected = {
            key
            for key, checkbox in self.positionFilters.items()
            if key != "all" and checkbox.isChecked()
        }
        allSelected = len(selected) == len(self.positionFilters) - 1
        allFilter = self.positionFilters["all"]
        blocker = QSignalBlocker(allFilter)
        allFilter.setChecked(allSelected)
        del blocker
        self.filterButton.setText(
            "Filter · All Positions" if allSelected else f"Filter · {len(selected)} units"
        )
        for row in range(self.table.rowCount()):
            groups = self._positionGroups(self._text(row, 1))
            self.table.setRowHidden(row, not bool(groups.intersection(selected)))
        self._goalkeeperColumnsUpdate()

    def _goalkeeperColumnsUpdate(self) -> None:
        """Expose goalkeeper-only facts only in an exclusively goalkeeper view."""

        if not hasattr(self, "table"):
            return
        selected = {
            key
            for key, checkbox in self.positionFilters.items()
            if key != "all" and checkbox.isChecked()
        }
        goalkeeperOnly = selected == {"goalkeepers"}
        for offset, attribute in enumerate(self.attributeNames, start=4):
            if attribute.casefold() in self.goalkeeperAttributeNames:
                self.table.setColumnHidden(offset, not goalkeeperOnly)

    def _traitEditorOpen(self, row: int, column: int) -> None:
        """Open the canonical checklist when the Known Traits cell is clicked."""

        if column != self.table.columnCount() - 1:
            return
        current = tuple(
            value.strip() for value in self._text(row, column).split(",") if value.strip()
        )
        dialog = PlayerTraitDialog(current, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.table.item(row, column).setText(", ".join(dialog.selectedTraits()))

    @staticmethod
    def _positionGroups(positions: str) -> set[str]:
        """Map FM's compact natural-position text into selectable tactical units."""

        compact = re.sub(r"\s+", "", positions.upper())
        groups: set[str] = set()
        if "GK" in compact:
            groups.add("goalkeepers")
        if "WB" in compact or re.search(r"(?:^|[,/])D(?:\(|[LCR]|$)", compact):
            groups.add("defenders")
        if "DM" in compact:
            groups.add("defensiveMidfielders")
        if re.search(r"(?:^|[,/])M(?:\(|[LCR]|$)", compact):
            groups.add("midfielders")
        if "AM" in compact:
            groups.add("attackingMidfielders")
        if "ST" in compact:
            groups.add("attackers")
        return groups


class SquadRolesTab(QWidget):
    """Show unique canonical roles and every squad candidate for the selected role."""

    def __init__(self, roles: tuple[RoleDisplay, ...], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.roles = roles
        layout = QVBoxLayout(self)
        if not roles:
            empty = QLabel(
                "No role assessment is available. Assign a complete tactic and define role "
                "assessment weights to begin."
            )
            empty.setObjectName("mutedText")
            empty.setWordWrap(True)
            layout.addWidget(empty)
            layout.addStretch()
            return

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.rolesByCode = {role.roleCode: role for role in roles}
        self.roleTable = QTableWidget(len(roles), 3, splitter)
        self.roleTable.setObjectName("roleAssessmentTable")
        self._tablePaletteApply(self.roleTable)
        self.roleTable.setHorizontalHeaderLabels(("Role", "Name", "Coverage"))
        self.roleTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.roleTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.roleTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.roleTable.setSortingEnabled(False)
        for row, role in enumerate(roles):
            abbreviation = QTableWidgetItem(role.abbreviation)
            abbreviation.setData(Qt.ItemDataRole.UserRole, role.roleCode)
            self.roleTable.setItem(row, 0, abbreviation)
            self.roleTable.setItem(row, 1, QTableWidgetItem(role.displayName))
            self.roleTable.setItem(row, 2, QTableWidgetItem(role.coverage))
        roleHeader = self.roleTable.horizontalHeader()
        roleHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        roleHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        roleHeader.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.roleTable.setSortingEnabled(True)
        self.candidateTable = QTableWidget(0, 5, splitter)
        self.candidateTable.setObjectName("roleCandidateTable")
        self._tablePaletteApply(self.candidateTable)
        self.candidateTable.setHorizontalHeaderLabels(
            (
                "Player",
                "Natural positions",
                "Generic Role Fit",
                "Best role",
                "Calculation breakdown",
            )
        )
        self.candidateTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.candidateTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.candidateTable.setWordWrap(True)
        candidateHeader = self.candidateTable.horizontalHeader()
        candidateHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        candidateHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        candidateHeader.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        candidateHeader.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        candidateHeader.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        splitter.addWidget(self.roleTable)
        splitter.addWidget(self.candidateTable)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter)
        self.roleTable.currentCellChanged.connect(self._roleShow)
        self.roleTable.selectRow(0)
        self.roleTable.setCurrentCell(0, 0)

    @staticmethod
    def _tablePaletteApply(table: QTableWidget) -> None:
        """Paint native viewport gaps with the squad table palette."""

        palette = table.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#101f2e"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#0c1926"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#f5f8fb"))
        table.setPalette(palette)
        table.viewport().setPalette(palette)
        table.viewport().setAutoFillBackground(True)

    def _roleShow(
        self,
        currentRow: int,
        _currentColumn: int,
        _previousRow: int,
        _previousColumn: int,
    ) -> None:
        if currentRow < 0:
            return
        roleItem = self.roleTable.item(currentRow, 0)
        if roleItem is None:
            return
        role = self.rolesByCode.get(str(roleItem.data(Qt.ItemDataRole.UserRole)))
        if role is None:
            return
        self.candidateTable.setSortingEnabled(False)
        self.candidateTable.setRowCount(len(role.candidates))
        for row, candidate in enumerate(role.candidates):
            for column, value in enumerate(
                (
                    candidate.name,
                    candidate.positions,
                    candidate.score,
                    candidate.bestRole,
                    candidate.breakdown,
                )
            ):
                sortValue = (
                    float(candidate.score)
                    if column == 2 and candidate.available
                    else -1.0 if column == 2 else value.casefold()
                )
                item = SortableTableWidgetItem(value, sortValue)
                self.candidateTable.setItem(row, column, item)
        self.candidateTable.resizeRowsToContents()
        self.candidateTable.setSortingEnabled(True)


class SortableTableWidgetItem(QTableWidgetItem):
    """Keep numeric and textual table sorting independent from display text."""

    def __init__(self, text: str, sortValue: object) -> None:
        super().__init__(text)
        self.sortValue = sortValue

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, SortableTableWidgetItem):
            return self.sortValue < other.sortValue
        return super().__lt__(other)
