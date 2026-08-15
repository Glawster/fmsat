"""Tab widgets composed by the squad detail workspace."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.squadDetailModel import RoleDisplay, SquadDetailModel
from fmsat.core.squadModel import SquadModel, SquadModelPlayer


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

    def __init__(self, model: SquadModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model = model
        self.attributeNames = tuple(
            sorted(
                {
                    name
                    for player in model.players
                    for name, _value in player.attributes
                }
            )
        )
        layout = QVBoxLayout(self)
        hint = QLabel(
            "Edit model values here. Saving preserves the screenshots as history and marks "
            "their evidence as superseded by this model. Attribute values must be 1–20."
        )
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        headers = ("Name", "Positions", "CA", "PA", *self.attributeNames)
        self.table = QTableWidget(len(model.players), len(headers), self)
        self.table.setObjectName("squadPlayersTable")
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        for row, player in enumerate(model.players):
            values = dict(player.attributes)
            for column, value in enumerate(
                (player.name, player.positions, player.ca, player.pa)
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))
            for offset, attribute in enumerate(self.attributeNames, start=4):
                value = values.get(attribute)
                self.table.setItem(
                    row,
                    offset,
                    QTableWidgetItem("" if value is None else str(value)),
                )
        self.table.resizeColumnsToContents()
        self.table.itemChanged.connect(lambda _item: self.changed.emit())
        layout.addWidget(self.table)

    def modelBuild(self) -> SquadModel:
        """Return validated edited values while retaining source provenance."""

        players = []
        for row, original in enumerate(self.model.players):
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
        self.roleList = QListWidget(splitter)
        self.roleList.setObjectName("roleAssessmentList")
        for role in roles:
            item = QListWidgetItem(
                f"{role.abbreviation}  {role.displayName}\n{role.coverage}"
            )
            item.setData(Qt.ItemDataRole.UserRole, role.roleCode)
            self.roleList.addItem(item)
        self.candidateTable = QTableWidget(0, 4, splitter)
        self.candidateTable.setObjectName("roleCandidateTable")
        self.candidateTable.setHorizontalHeaderLabels(
            ("Player", "Natural positions", "Generic Role Fit", "Calculation breakdown")
        )
        self.candidateTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.candidateTable.setWordWrap(True)
        splitter.addWidget(self.roleList)
        splitter.addWidget(self.candidateTable)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter)
        self.roleList.currentRowChanged.connect(self._roleShow)
        self.roleList.setCurrentRow(0)

    def _roleShow(self, index: int) -> None:
        if not 0 <= index < len(self.roles):
            return
        role = self.roles[index]
        self.candidateTable.setRowCount(len(role.candidates))
        for row, candidate in enumerate(role.candidates):
            for column, value in enumerate(
                (candidate.name, candidate.positions, candidate.score, candidate.breakdown)
            ):
                item = QTableWidgetItem(value)
                if not candidate.available:
                    item.setForeground(QColor("#f4c65d"))
                self.candidateTable.setItem(row, column, item)
        self.candidateTable.resizeColumnsToContents()
        self.candidateTable.resizeRowsToContents()
