"""Reusable plain-English explanation dialog for Tactic Analysis rows."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from fmsat.app.tacticAnalysisDisplay import TacticExplanationDisplay


class TacticAnalysisExplanationDialog(QDialog):
    """Show meaning, football context, and deterministic calculation evidence."""

    def __init__(
        self,
        explanation: TacticExplanationDisplay,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("tacticAnalysisExplanationDialog")
        self.setWindowTitle("Explain this")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        title = QLabel(explanation.title)
        title.setObjectName("cardTitle")
        title.setWordWrap(True)
        layout.addWidget(title)
        self._sectionAdd(layout, "What this means", explanation.meaning)
        self._sectionAdd(layout, "Football meaning", explanation.footballMeaning)
        self._sectionAdd(layout, "How FMSAT calculated it", explanation.calculation)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _sectionAdd(layout: QVBoxLayout, headingText: str, bodyText: str) -> None:
        heading = QLabel(headingText)
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        body = QLabel(bodyText)
        body.setObjectName("mutedText")
        body.setWordWrap(True)
        layout.addWidget(body)
