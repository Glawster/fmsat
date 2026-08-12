"""Validation summary widget for the tactic Overview tab."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class BuildIssue(Protocol):
    """Issue fields presented by the validation widget."""

    message: str


class BuildResult(Protocol):
    """Read-only object-model build result consumed by the widget."""

    tactic: object | None
    issues: Sequence[BuildIssue]
    complete: bool
    confirmed: bool


class TacticValidationWidget(QFrame):
    """Present one object-model build result without performing validation."""

    def __init__(
        self,
        result: BuildResult | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("validationPanel")
        self._layoutCreate()
        self.resultShow(result)

    def resultShow(self, result: BuildResult | None) -> None:
        """Refresh the widget from an object-model build result."""

        self._contentClear()

        if result is None:
            self._emptyShow()
            return

        status, detail, state = self._statusDescribe(result)
        self.statusLabel.setText(status)
        self.statusLabel.setProperty("validationState", state)
        self.statusLabel.style().unpolish(self.statusLabel)
        self.statusLabel.style().polish(self.statusLabel)
        self.detailLabel.setText(detail)

        self._phaseAdd("In Possession", self._positionCount(result, "inPossession"))
        self._phaseAdd("Out Of Possession", self._positionCount(result, "outOfPossession"))

        if result.issues:
            for issue in result.issues:
                self._issueAdd(issue.message)
        else:
            self._issueAdd("No validation issues were reported.", issue=False)

    ## layout

    def _layoutCreate(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        headingRow = QHBoxLayout()
        heading = QLabel("Tactic Validation")
        heading.setObjectName("cardTitle")
        headingRow.addWidget(heading)
        headingRow.addStretch()
        self.statusLabel = QLabel()
        self.statusLabel.setObjectName("validationStatus")
        headingRow.addWidget(self.statusLabel)
        layout.addLayout(headingRow)

        self.detailLabel = QLabel()
        self.detailLabel.setObjectName("mutedText")
        self.detailLabel.setWordWrap(True)
        layout.addWidget(self.detailLabel)

        self.content = QWidget()
        self.contentLayout = QVBoxLayout(self.content)
        self.contentLayout.setContentsMargins(0, 0, 0, 0)
        self.contentLayout.setSpacing(7)
        layout.addWidget(self.content)
        layout.addStretch()

    ## content

    def _contentClear(self) -> None:
        while self.contentLayout.count():
            item = self.contentLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _emptyShow(self) -> None:
        self.statusLabel.setText("Not checked")
        self.statusLabel.setProperty("validationState", "unknown")
        self.statusLabel.style().unpolish(self.statusLabel)
        self.statusLabel.style().polish(self.statusLabel)
        self.detailLabel.setText(
            "Validation will appear when the stored tactic has been loaded into the "
            "football object model."
        )

    def _issueAdd(self, message: str, *, issue: bool = True) -> None:
        label = QLabel(f"●  {message}")
        label.setObjectName("validationIssue" if issue else "validationPassed")
        label.setWordWrap(True)
        self.contentLayout.addWidget(label)

    def _phaseAdd(self, title: str, count: int | None) -> None:
        row = QFrame()
        row.setObjectName("validationPhase")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(9, 6, 9, 6)

        label = QLabel(title)
        label.setObjectName("validationPhaseName")
        layout.addWidget(label, 1)

        if count is None:
            value = "Unavailable"
            state = "unknown"
        else:
            value = f"{count} of 11 positions"
            state = "passed" if count == 11 else "warning"

        countLabel = QLabel(value)
        countLabel.setObjectName("validationPhaseCount")
        countLabel.setProperty("validationState", state)
        countLabel.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(countLabel)
        self.contentLayout.addWidget(row)

    ## result

    @staticmethod
    def _positionCount(result: BuildResult, phase: str) -> int | None:
        if result.tactic is None:
            return None
        formation = getattr(result.tactic, phase, None)
        if formation is None:
            return None
        return len(formation.positions)

    @staticmethod
    def _statusDescribe(result: BuildResult) -> tuple[str, str, str]:
        if result.tactic is None:
            return (
                "Unable to build",
                "The stored data could not produce both required tactical phases.",
                "error",
            )
        if not result.confirmed:
            return (
                "Review required",
                "The object model was built, but its structured extraction is not confirmed.",
                "warning",
            )
        if not result.complete:
            return (
                "Incomplete",
                "The object model was built, but stored data or phase coverage is incomplete.",
                "warning",
            )
        if result.issues:
            return (
                "Attention required",
                "The object model is complete and confirmed, with reported validation issues.",
                "warning",
            )
        return (
            "Validated",
            "The object model is complete, confirmed, and has no reported issues.",
            "passed",
        )
