"""Tab widgets composed by the tactic detail workspace."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.tacticDetailModel import DisplaySlot, TacticDetailModel
from fmsat.app.tacticPitchWidget import PitchWidget
from fmsat.app.tacticValidationWidget import BuildResult, TacticValidationWidget


class AnalysisTab(QWidget):
    """Explain the unavailable generated-analysis state."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addStretch()
        icon = QLabel("◇")
        icon.setObjectName("emptyIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)
        title = QLabel("Analysis Is Ready When You Are")
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        copy = QLabel(
            "Generated analysis will appear here, clearly separated from imported and "
            "user-entered facts. No tactical conclusions have been generated yet."
        )
        copy.setObjectName("mutedText")
        copy.setWordWrap(True)
        copy.setMaximumWidth(560)
        copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyRow = QHBoxLayout()
        copyRow.addStretch()
        copyRow.addWidget(copy)
        copyRow.addStretch()
        layout.addLayout(copyRow)
        generate = QPushButton("Generate analysis")
        generate.setEnabled(False)
        generate.setToolTip("Analysis algorithms are outside this prototype")
        buttonRow = QHBoxLayout()
        buttonRow.addStretch()
        buttonRow.addWidget(generate)
        buttonRow.addStretch()
        layout.addLayout(buttonRow)
        layout.addStretch()


class InstructionsTab(QScrollArea):
    """Present stored team instructions grouped by phase."""

    def __init__(self, model: TacticDetailModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        grid = QGridLayout(content)
        for index, (title, instructions) in enumerate(model.instructionGroups):
            grid.addWidget(self._instructionCard(title, instructions), index // 2, index % 2)
        self.setWidget(content)

    @staticmethod
    def _instructionCard(title: str, instructions: tuple[tuple[str, str], ...]) -> QFrame:
        card = QFrame()
        card.setObjectName("instructionCard")
        layout = QVBoxLayout(card)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        layout.addWidget(heading)
        for name, value in instructions:
            row = QHBoxLayout()
            key = QLabel(name)
            key.setObjectName("mutedText")
            row.addWidget(key, 1)
            pill = QLabel(value)
            pill.setObjectName("valuePill")
            row.addWidget(pill)
            layout.addLayout(row)
        layout.addStretch()
        return card


class OverviewTab(QWidget):
    """Summarize the current formation, stored facts, and notes."""

    def __init__(
        self,
        model: TacticDetailModel,
        validation: BuildResult | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.addWidget(self._pitchPanel(model), 2)
        side = QVBoxLayout()
        if model.status.casefold().startswith("incomplete"):
            side.addWidget(self._incompleteBanner())
        side.addWidget(self._summaryPanel(model), 1)
        side.addWidget(self._notesPanel(model.notes), 1)
        self.validationWidget = TacticValidationWidget(validation)
        side.addWidget(self.validationWidget, 1)
        layout.addLayout(side, 3)

    @staticmethod
    def _incompleteBanner() -> QFrame:
        """Highlight when the tactic is visible but data coverage is incomplete."""

        banner = QFrame()
        banner.setObjectName("incompleteBanner")
        layout = QVBoxLayout(banner)
        title = QLabel("Incomplete Tactic Data")
        title.setObjectName("incompleteBannerTitle")
        layout.addWidget(title)
        copy = QLabel(
            "This tactic is accessible, but structured or saved model data is missing. "
            "Import and confirm tactic screenshots to complete this view."
        )
        copy.setObjectName("incompleteBannerText")
        copy.setWordWrap(True)
        layout.addWidget(copy)
        return banner

    def validationShow(self, result: BuildResult | None) -> None:
        """Refresh the overview's object-model validation summary."""

        self.validationWidget.resultShow(result)

    @staticmethod
    def _notesPanel(notes: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("overviewPanel")
        layout = QVBoxLayout(panel)
        title = QLabel("Notes")
        title.setObjectName("cardTitle")
        layout.addWidget(title)
        note = QLabel(notes)
        note.setObjectName("mutedText")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        return panel

    @staticmethod
    def _pitchPanel(model: TacticDetailModel) -> QFrame:
        panel = QFrame()
        panel.setObjectName("pitchPanel")
        layout = QVBoxLayout(panel)
        title = QLabel("Current Formation")
        title.setObjectName("cardTitle")
        layout.addWidget(title)
        pitch = PitchWidget(model.formationSlots)
        # The overview owns 40% of its responsive row, so its pitch must not
        # force that proportion wider through the reusable pitch minimum.
        pitch.setMinimumWidth(0)
        layout.addWidget(pitch)
        return panel

    @staticmethod
    def _summaryPanel(model: TacticDetailModel) -> QFrame:
        panel = QFrame()
        panel.setObjectName("overviewPanel")
        layout = QVBoxLayout(panel)
        heading = QLabel("Captured Summary")
        heading.setObjectName("cardTitle")
        layout.addWidget(heading)
        for title, copy in model.summaryItems:
            item = QLabel(f"<b>{title}</b><br><span style='color:#8fa3b8'>{copy}</span>")
            item.setObjectName("summaryItem")
            layout.addWidget(item)
        layout.addStretch()
        return panel


class ShapeTab(QWidget):
    """Compare in- and out-of-possession formation shapes."""

    def __init__(self, model: TacticDetailModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.addWidget(self._phasePanel("In Possession", model.formationSlots), 1)
        layout.addWidget(self._phasePanel("Out Of Possession", model.outOfPossessionSlots), 1)

    @staticmethod
    def _phasePanel(title: str, slots: tuple[DisplaySlot, ...]) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        layout.addWidget(heading)
        hint = QLabel("Role · canonical position · duty")
        hint.setObjectName("mutedText")
        layout.addWidget(hint)
        layout.addWidget(PitchWidget(slots))
        return panel
