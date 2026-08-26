"""Shared visual building blocks for FMSAT object workspaces."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class FactCard(QFrame):
    """Render one consistently styled workspace summary fact."""

    activated = Signal()

    def __init__(self, label: str, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("factCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(2)

        self.keyLabel = QLabel(label, self)
        self.keyLabel.setObjectName("factKey")
        layout.addWidget(self.keyLabel)

        self.valueLabel = QLabel(value, self)
        self.valueLabel.setObjectName("factValue")
        self.valueLabel.setWordWrap(True)
        layout.addWidget(self.valueLabel)

    def interactionEnable(self, tooltip: str) -> None:
        """Make this fact card advertise and emit a navigation action."""

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setAccessibleDescription(tooltip)
        self.setProperty("interactive", True)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Activate interactive cards on a primary-button click."""

        if self.property("interactive") and event.button() is Qt.MouseButton.LeftButton:
            self.activated.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class WorkspaceHeader:
    """Build the common back-button, heading and action layout used by workspaces."""

    def __init__(
        self,
        *,
        workspace: str,
        context: str,
        title: str,
        backRequested: Callable[[], None],
        titleActions: Iterable[QWidget] = (),
        trailingActions: Iterable[QWidget] = (),
    ) -> None:
        self.layout = QHBoxLayout()
        self.layout.setSpacing(18)

        back = QPushButton("←  FMSAT Workspace")
        back.setObjectName("quietButton")
        back.clicked.connect(backRequested)
        self.layout.addWidget(back, 0, Qt.AlignmentFlag.AlignVCenter)

        heading = QVBoxLayout()
        heading.setSpacing(2)
        workspaceLabel = QLabel(f"{workspace} Workspace  ·  {context}")
        workspaceLabel.setObjectName("workspaceHeading")
        heading.addWidget(workspaceLabel)

        titleRow = QHBoxLayout()
        titleRow.setSpacing(12)
        self.titleLabel = QLabel(title)
        self.titleLabel.setObjectName("pageTitle")
        titleRow.addWidget(self.titleLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        for widget in titleActions:
            titleRow.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
        titleRow.addStretch()
        heading.addLayout(titleRow)
        self.layout.addLayout(heading, 1)

        for widget in trailingActions:
            self.layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
