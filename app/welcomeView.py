"""Welcome workspace for navigating locally stored FMSAT data."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from organiseMyProjects.logUtils import getLogger
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from fmsat.database import Database, DatabaseError
from fmsat.database.records import SquadRecord, TacticRecord

logger = getLogger()


class WelcomeService:
    """Load bounded dashboard records through the existing database gateway."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def summariesLoad(self) -> tuple[list[TacticRecord], list[SquadRecord]]:
        """Return tactic and squad summaries without loading player snapshots."""

        tactics = self.database.tacticRecords()
        squads = self.database.squadRecords()
        return (
            tactics if isinstance(tactics, list) else [],
            squads if isinstance(squads, list) else [],
        )


class WelcomeView(QWidget):
    """Low-interaction startup dashboard and navigation hub."""

    def __init__(
        self,
        service: WelcomeService,
        actions: tuple[QAction, ...],
        tacticOpen: Callable[[str], None],
        squadOpen: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.tacticOpen = tacticOpen
        self.squadOpen = squadOpen
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
                "background-color: #2563eb; color: white; border: 2px solid #1d4ed8; "
                "border-radius: 10px; font-size: 15px; font-weight: 600; padding: 8px 18px;"
                "}"
                "QToolButton#workspaceActionButton:hover {"
                "background-color: #3b82f6; border-color: #1e40af;"
                "}"
                "QToolButton#workspaceActionButton:pressed {"
                "background-color: #1d4ed8;"
                "}"
                "QToolButton#workspaceActionButton:focus {"
                "background-color: #2563eb; border-color: #93c5fd;"
                "}"
                "QToolButton#workspaceActionButton:focus:hover {"
                "background-color: #3b82f6; border-color: #93c5fd;"
                "}"
                "QToolButton#workspaceActionButton:focus:pressed {"
                "background-color: #1d4ed8; border-color: #93c5fd;"
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
        self.refresh()

    def refresh(self) -> None:
        """Reload visible summaries from committed local state."""

        while self.summaryLayout.count():
            item = self.summaryLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        try:
            tactics, squads = self.service.summariesLoad()
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
        opened: Callable[[], None],
        image: str | None = None,
        placeholder: str = "No image",
    ) -> None:
        card = QFrame(self.summaryWidget)
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setObjectName("summaryCard")
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
        openButton = QPushButton("Open")
        openButton.setAccessibleName(f"Open {name}")
        openButton.clicked.connect(opened)
        layout.addWidget(openButton)
        self.summaryLayout.addWidget(card)

    def _tacticsAdd(self, records: list[TacticRecord]) -> None:
        self._sectionHeadingAdd("Tactics", len(records))
        if not records:
            self._emptyAdd("No tactics have been imported yet.", self._actionFind("Import Tactic"))
            return
        for record in records:
            detail = f"Formation not recorded · {record.captureCount} captures"
            self._summaryAdd(
                record.name,
                detail,
                lambda _checked=False, name=record.name: self.tacticOpen(name),
                record.formationImage,
                "No formation image",
            )

    def _actionFind(self, text: str) -> QAction:
        action = self.actionsByText.get(text)
        if action is not None:
            return action
        unavailable = QAction(text, self)
        unavailable.setEnabled(False)
        unavailable.setToolTip("This action is not available in the current application context.")
        return unavailable
