"""Welcome workspace for navigating locally stored FMSAT data."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fmsat.core.logUtils import getLogger
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.colourPalette import (
    button as buttonColour,
    buttonBorder,
    buttonSelected,
)

from fmsat.core.parser import TacticVocabulary
from fmsat.core.roleKnowledge import RoleKnowledgeService
from fmsat.core.rolePositionCompatibility import (
    RolePositionFamilyPolicy,
    capturedRolePositionFamilies,
)
from fmsat.database import Database, DatabaseError
from fmsat.database.records import SquadRecord, TacticRecord

logger = getLogger()


@dataclass(frozen=True, slots=True)
class CapturedRoleSummary:
    """One confirmed role definition shown on the welcome dashboard."""

    reference: str
    displayName: str
    abbreviations: tuple[str, ...]
    positions: tuple[str, ...]
    duties: tuple[str, ...]
    behaviours: tuple[str, ...]


class SummaryCard(QFrame):
    """Keyboard- and pointer-selectable welcome summary card."""

    activated = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in {Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Space}:
            self.activated.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton:
            self.activated.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class PositionRoleGroup(QWidget):
    """Collapsible collection of captured roles for one tactical position."""

    def __init__(self, position: str, roleCount: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("positionRoleGroup")
        self.setProperty("position", position)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.summaryButton = QToolButton(self)
        self.summaryButton.setObjectName("positionSummaryButton")
        self.summaryButton.setProperty("position", position)
        roleLabel = "role" if roleCount == 1 else "roles"
        self.summaryButton.setText(f"{position} — {roleCount} {roleLabel}")
        self.summaryButton.setCheckable(True)
        self.summaryButton.setChecked(False)
        self.summaryButton.setArrowType(Qt.ArrowType.NoArrow)
        self.summaryButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.summaryButton.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.summaryButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.summaryButton.setStyleSheet(
            "QToolButton#positionSummaryButton {"
            "background: #31b98f; color: #061510; font-weight: 700; text-align: left; "
            "padding: 9px 12px; border: 0; border-radius: 7px;"
            "}"
            "QToolButton#positionSummaryButton:hover { background: #56d6b0; }"
            "QToolButton#positionSummaryButton:pressed, "
            "QToolButton#positionSummaryButton:checked { background: #28a77f; }"
        )
        layout.addWidget(self.summaryButton)

        self.rolesContainer = QWidget(self)
        self.rolesContainer.setObjectName("positionRolesContainer")
        self.rolesLayout = QVBoxLayout(self.rolesContainer)
        self.rolesLayout.setContentsMargins(16, 0, 0, 4)
        self.rolesLayout.setSpacing(4)
        self.rolesContainer.setVisible(False)
        layout.addWidget(self.rolesContainer)

        self.summaryButton.toggled.connect(self._expandedSet)

    def _expandedSet(self, expanded: bool) -> None:
        self.rolesContainer.setVisible(expanded)


class WelcomeService:
    """Load bounded dashboard records through the existing database gateway."""

    def __init__(
        self,
        database: Database,
        tacticVocabulary: TacticVocabulary | None = None,
        roleKnowledgeService: RoleKnowledgeService | None = None,
    ) -> None:
        self.database = database
        self.tacticVocabulary = tacticVocabulary
        self.roleKnowledgeService = roleKnowledgeService
        self.positionFamilyPolicy = RolePositionFamilyPolicy.load()

    def rolePositionFamilies(self, role: CapturedRoleSummary) -> tuple[str, ...]:
        """Resolve catalogue families through the shared compatibility policy."""

        return capturedRolePositionFamilies(
            role.reference,
            role.positions,
            self.positionFamilyPolicy,
        )

    def summariesLoad(
        self,
    ) -> tuple[list[TacticRecord], list[SquadRecord], list[CapturedRoleSummary]]:
        """Return dashboard summaries without loading player snapshots."""

        tactics = self.database.tacticRecords()
        squads = self.database.squadRecords()
        roles = []
        if self.tacticVocabulary is not None and self.roleKnowledgeService is not None:
            definitions = self.roleKnowledgeService.definitionsList()
            if isinstance(definitions, (list, tuple)):
                roles = sorted(
                    (
                        CapturedRoleSummary(
                            reference=(
                                definition.roleCode
                                if definition.roleCode is not None
                                else f"roleID:{definition.roleID}"
                            ),
                            displayName=definition.displayName,
                            abbreviations=definition.abbreviations,
                            positions=definition.positions,
                            duties=definition.duties,
                            behaviours=definition.behaviours,
                        )
                        for definition in definitions
                    ),
                    key=self.roleSortKey,
                )
            else:
                capturedRoles = (
                    (
                        role,
                        self.roleKnowledgeService.definitionLoad(role.code),
                    )
                    for role in self.tacticVocabulary.roles.values()
                    if self.roleKnowledgeService.definitionExists(role.code)
                )
                roles = sorted(
                    (
                        CapturedRoleSummary(
                            reference=role.code,
                            displayName=role.displayName,
                            abbreviations=role.abbreviations,
                            positions=role.positions,
                            duties=role.duties,
                            behaviours=(
                                tuple(str(value) for value in content.get("behaviours", []))
                                if isinstance(content, dict)
                                else ()
                            ),
                        )
                        for role, content in capturedRoles
                    ),
                    key=self.roleSortKey,
                )
        return (
            tactics if isinstance(tactics, list) else [],
            squads if isinstance(squads, list) else [],
            roles,
        )

    @staticmethod
    def positionSortKey(position: str) -> tuple[int, str]:
        """Order one position from the attacking line back to goalkeeper."""

        if position.startswith("ST"):
            rank = 0
        elif position.startswith("AM"):
            rank = 1
        elif position.startswith("DM"):
            rank = 3
        elif position.startswith("M"):
            rank = 2
        elif position.startswith("D") or position.startswith("WB"):
            rank = 4
        elif position == "GK":
            rank = 5
        else:
            rank = 6
        return rank, position

    @classmethod
    def roleSortKey(cls, role) -> tuple[int, str]:
        """Order one role by its highest tactical line and then its name."""

        rank = min((cls.positionSortKey(position)[0] for position in role.positions), default=6)
        return rank, role.displayName.casefold()


class WelcomeView(QWidget):
    """Low-interaction startup dashboard and navigation hub."""

    def __init__(
        self,
        service: WelcomeService,
        actions: tuple[QAction, ...],
        tacticOpen: Callable[[str], None],
        tacticProcess: Callable[[str], None] | None,
        squadOpen: Callable[[str], None],
        roleOpen: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.tacticOpen = tacticOpen
        self.tacticProcess = tacticProcess
        self.squadOpen = squadOpen
        self.roleOpen = roleOpen
        self.actionsByText = {action.text(): action for action in actions}
        self.setObjectName("welcomeView")

        rootLayout = QHBoxLayout(self)
        actionPanel = QWidget(self)
        actionPanel.setMaximumWidth(300)
        actionLayout = QVBoxLayout(actionPanel)
        heading = QLabel("FMSAT Workspace")
        heading.setStyleSheet("font-size: 20px; font-weight: bold;")
        actionLayout.addWidget(heading)
        actionLayout.addWidget(QLabel("Choose what you want to do next."))
        for action in actions:
            button = QToolButton(actionPanel)
            button.setDefaultAction(action)
            button.setObjectName("workspaceActionButton")
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setAccessibleName(action.text())
            button.setFixedSize(220, 54)
            button.setStyleSheet(
                "QToolButton#workspaceActionButton {"
                f"background-color: {buttonColour}; color: white; "
                f"border: 2px solid {buttonBorder}; "
                "border-radius: 10px; font-size: 15px; font-weight: 600; padding: 8px 18px;"
                "}"
                "QToolButton#workspaceActionButton:hover {"
                f"background-color: {buttonSelected}; border-color: {buttonBorder};"
                "}"
                "QToolButton#workspaceActionButton:pressed {"
                f"background-color: {buttonBorder};"
                "}"
                "QToolButton#workspaceActionButton:focus {"
                f"background-color: {buttonColour}; border-color: {buttonBorder};"
                "}"
                "QToolButton#workspaceActionButton:focus:hover {"
                f"background-color: {buttonSelected}; border-color: {buttonBorder};"
                "}"
                "QToolButton#workspaceActionButton:focus:pressed {"
                f"background-color: {buttonBorder}; border-color: {buttonBorder};"
                "}"
            )
            buttonRow = QHBoxLayout()
            buttonRow.addStretch()
            buttonRow.addWidget(button)
            buttonRow.addStretch()
            actionLayout.addLayout(buttonRow)
        actionLayout.addStretch()
        rootLayout.addWidget(actionPanel)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.summaryWidget = QWidget(scroll)
        self.summaryLayout = QVBoxLayout(self.summaryWidget)
        scroll.setWidget(self.summaryWidget)
        rootLayout.addWidget(scroll, 1)

        rolesPanel = QFrame(self)
        rolesPanel.setObjectName("rolesPanel")
        rolesPanel.setFrameShape(QFrame.Shape.StyledPanel)
        rolesPanel.setMinimumWidth(380)
        rolesPanelLayout = QVBoxLayout(rolesPanel)
        rolesHeading = QLabel("Captured Roles")
        rolesHeading.setStyleSheet("font-size: 17px; font-weight: bold;")
        rolesPanelLayout.addWidget(rolesHeading)
        rolesScroll = QScrollArea(rolesPanel)
        rolesScroll.setWidgetResizable(True)
        rolesScroll.setFrameShape(QFrame.Shape.NoFrame)
        self.rolesWidget = QWidget(rolesScroll)
        self.rolesLayout = QVBoxLayout(self.rolesWidget)
        rolesScroll.setWidget(self.rolesWidget)
        rolesPanelLayout.addWidget(rolesScroll)
        rootLayout.addWidget(rolesPanel, 1)
        self.refresh()

    def refresh(self) -> None:
        """Reload visible summaries from committed local state."""

        while self.summaryLayout.count():
            item = self.summaryLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        while self.rolesLayout.count():
            item = self.rolesLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        try:
            tactics, squads, roles = self.service.summariesLoad()
        except DatabaseError as exc:
            logger.warning("welcome summaries unavailable: %s", exc)
            error = QLabel(f"Stored data could not be loaded.\n{exc}")
            error.setObjectName("welcomeError")
            error.setWordWrap(True)
            self.summaryLayout.addWidget(error)
            self.summaryLayout.addStretch()
            return

        if not tactics and not squads:
            introduction = QLabel(
                "Welcome to FMSAT. Import your first tactic or squad to begin building "
                "your workspace."
            )
            introduction.setObjectName("welcomeIntroduction")
            introduction.setWordWrap(True)
            self.summaryLayout.addWidget(introduction)
        self._tacticsAdd(tactics)
        self._squadsAdd(squads)
        self._rolesAdd(roles)
        self.summaryLayout.addStretch()

    def _emptyAdd(self, message: str, action: QAction) -> None:
        container = QWidget(self.summaryWidget)
        layout = QHBoxLayout(container)
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label, 1)
        button = QToolButton(container)
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        layout.addWidget(button)
        self.summaryLayout.addWidget(container)

    def _sectionHeadingAdd(self, title: str, count: int) -> None:
        heading = QLabel(f"{title} ({count})")
        heading.setStyleSheet("font-size: 17px; font-weight: bold; margin-top: 12px;")
        heading.setObjectName(f"{title.lower()}Heading")
        self.summaryLayout.addWidget(heading)

    def _rolesAdd(self, roles: list[CapturedRoleSummary]) -> None:
        count = QLabel(f"Roles ({len(roles)})")
        count.setObjectName("rolesHeading")
        count.setStyleSheet("font-weight: bold;")
        self.rolesLayout.addWidget(count)
        if not roles:
            empty = QLabel("No role profiles have been captured yet.")
            empty.setWordWrap(True)
            self.rolesLayout.addWidget(empty)
            self.rolesLayout.addStretch()
            return
        rolesByPosition: dict[str, dict[str, CapturedRoleSummary]] = {}
        for summary in roles:
            families = self.service.rolePositionFamilies(summary) or ("Unassigned",)
            for family in families:
                rolesByPosition.setdefault(family, {})[summary.reference] = summary

        for position in sorted(rolesByPosition, key=self.service.positionSortKey):
            positionRoles = sorted(
                rolesByPosition[position].values(),
                key=lambda summary: summary.displayName.casefold(),
            )
            group = PositionRoleGroup(position, len(positionRoles), self.rolesWidget)
            self.rolesLayout.addWidget(group)
            for summary in positionRoles:
                self._roleAdd(summary, group.rolesLayout, group.rolesContainer)
        self.rolesLayout.addStretch()

    def _roleAdd(
        self,
        summary: CapturedRoleSummary,
        targetLayout: QVBoxLayout,
        targetParent: QWidget,
    ) -> None:
        """Add one captured role card beneath its position summary row."""

        abbreviation = (
            summary.abbreviations[0]
            if summary.abbreviations
            else summary.reference.replace("roleID:", "Role ")
        )
        positions = ", ".join(summary.positions)
        duties = ", ".join(duty.title() for duty in summary.duties)
        behaviours = ", ".join(self._behaviourLabel(value) for value in summary.behaviours)
        detail = "\n".join(
            (
                f"Behaviours: {behaviours or 'None'}",
                f"Positions: {positions}",
                f"Duties: {duties or 'Unknown'}",
            )
        )
        self._summaryAdd(
            summary.displayName,
            detail,
            (
                lambda _checked=False, reference=summary.reference: (
                    self.roleOpen(reference) if self.roleOpen is not None else None
                )
            ),
            placeholder=abbreviation,
            targetLayout=targetLayout,
            targetParent=targetParent,
        )

    def _squadsAdd(self, records: list[SquadRecord]) -> None:
        self._sectionHeadingAdd("Squads", len(records))
        if not records:
            self._emptyAdd("No squads have been imported yet.", self._actionFind("Import Squad"))
            return
        for record in records:
            detail = f"{record.playerCount} players · {record.captureCount} captures"
            self._summaryAdd(
                record.name,
                detail,
                lambda _checked=False, name=record.name: self.squadOpen(name),
                getattr(record, "clubImage", None),
                placeholder="No club information image",
            )

    def _summaryAdd(
        self,
        name: str,
        detail: str,
        opened: Callable[[], None] | None,
        image: str | None = None,
        placeholder: str = "No image",
        actionText: str | None = None,
        actionTriggered: Callable[[], None] | None = None,
        targetLayout: QVBoxLayout | None = None,
        targetParent: QWidget | None = None,
    ) -> None:
        parent = targetParent if targetParent is not None else self.summaryWidget
        card = SummaryCard(parent)
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setObjectName("summaryCard")
        card.setProperty("summaryName", name)
        if opened is not None:
            card.setAccessibleName(name)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            card.activated.connect(opened)
        layout = QHBoxLayout(card)
        thumbnail = QLabel(placeholder)
        thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail.setFixedSize(140, 80)
        if image and Path(image).is_file():
            pixmap = QPixmap(image)
            if not pixmap.isNull():
                thumbnail.setPixmap(
                    pixmap.scaled(
                        thumbnail.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                thumbnail.setText("")
        layout.addWidget(thumbnail)
        textLayout = QVBoxLayout()
        nameLabel = QLabel(name)
        nameLabel.setStyleSheet("font-weight: bold;")
        textLayout.addWidget(nameLabel)
        textLayout.addWidget(QLabel(detail))
        layout.addLayout(textLayout, 1)
        if actionText and actionTriggered is not None:
            button = QToolButton(card)
            button.setText(actionText)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.clicked.connect(actionTriggered)
            layout.addWidget(button)
        destination = targetLayout if targetLayout is not None else self.summaryLayout
        destination.addWidget(card)

    @staticmethod
    def _behaviourLabel(value: str) -> str:
        words = re.sub(r"(?<!^)(?=[A-Z])", " ", value).replace("_", " ")
        return words.title()

    def _tacticsAdd(self, records: list[TacticRecord]) -> None:
        self._sectionHeadingAdd("Tactics", len(records))
        if not records:
            self._emptyAdd("No tactics have been imported yet.", self._actionFind("Import Tactic"))
            return
        for record in records:
            detail = f"Formation not recorded · {record.captureCount} captures"
            needsProcessing = record.captureCount > 0 and not getattr(
                record, "hasObjectModelData", False
            )
            self._summaryAdd(
                record.name,
                detail,
                lambda _checked=False, name=record.name: self.tacticOpen(name),
                record.formationImage,
                "No formation image",
                actionText="Process" if needsProcessing else None,
                actionTriggered=(
                    (lambda _checked=False, name=record.name: self.tacticProcess(name))
                    if needsProcessing and self.tacticProcess is not None
                    else None
                ),
            )

    def _actionFind(self, text: str) -> QAction:
        action = self.actionsByText.get(text)
        if action is not None:
            return action
        unavailable = QAction(text, self)
        unavailable.setEnabled(False)
        unavailable.setToolTip("This action is not available in the current application context.")
        return unavailable
