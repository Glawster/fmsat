"""Focused editor for factual player data in the current squad model."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.presentation import (
    attributeIsGoalkeeperOnly,
    playerIsGoalkeeper,
    playerNameDisplay,
    playerNameStorage,
)
from fmsat.app.squadDetailTabs import PlayerTraitDialog
from fmsat.core.config import AttributeDefinition
from fmsat.core.squadModel import SquadModelPlayer


class PlayerEditorDialog(QDialog):
    """Edit one player's persisted squad facts without exposing derived role scores."""

    def __init__(
        self,
        player: SquadModelPlayer,
        attributes: tuple[AttributeDefinition, ...],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.player = player
        self.attributes = attributes
        self.selectedTraits = player.traits
        self.attributeInputs: dict[str, QSpinBox] = {}
        self.setObjectName("playerEditorDialog")
        self.setWindowTitle(f"Edit Player · {playerNameDisplay(player.name)}")
        self.resize(900, 720)
        self.setMinimumSize(780, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        context = QLabel(
            "Edit factual player-model evidence here. Generic Role Fit, role depth and squad "
            "findings are derived automatically after the player is saved."
        )
        context.setObjectName("playerEditorContext")
        context.setWordWrap(True)
        layout.addWidget(context)

        identityGroup = QGroupBox("Player", self)
        identityGroup.setObjectName("playerEditorSection")
        identity = QFormLayout(identityGroup)
        identity.setContentsMargins(12, 14, 12, 12)
        identity.setHorizontalSpacing(14)
        identity.setVerticalSpacing(8)
        self.nameInput = QLineEdit(playerNameDisplay(player.name), identityGroup)
        self.positionsInput = QLineEdit(player.positions, identityGroup)
        self.caInput = QLineEdit(player.ca, identityGroup)
        self.paInput = QLineEdit(player.pa, identityGroup)
        identity.addRow("Name", self.nameInput)
        identity.addRow("Natural positions", self.positionsInput)
        identity.addRow("CA", self.caInput)
        identity.addRow("PA", self.paInput)
        stateLabel = (
            "Uncertain name — review recommended"
            if player.validationState == "uncertain"
            else player.validationState.title()
        )
        provenance = stateLabel + (
            f" · source import {player.sourceImportSessionId}"
            if player.sourceImportSessionId is not None
            else ""
        )
        evidence = QLabel(provenance, identityGroup)
        evidence.setObjectName("playerEvidenceStatus")
        identity.addRow("Evidence status", evidence)
        layout.addWidget(identityGroup)

        scroll = QScrollArea(self)
        scroll.setObjectName("playerAttributeScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        attributeContainer = QWidget(scroll)
        attributeContainer.setObjectName("playerAttributeContainer")
        attributeLayout = QGridLayout(attributeContainer)
        attributeLayout.setContentsMargins(12, 10, 12, 10)
        attributeLayout.setHorizontalSpacing(20)
        attributeLayout.setVerticalSpacing(8)
        values = dict(player.attributes)
        definitions = tuple(
            definition
            for definition in self._attributeDefinitions(values)
            if playerIsGoalkeeper(player.positions)
            or not attributeIsGoalkeeperOnly(definition.name)
        )
        # Full attribute names need more horizontal room than the compact squad table.
        # Three label/value groups per row remains readable at the minimum dialog width.
        for index, definition in enumerate(definitions):
            row = index // 3
            column = (index % 3) * 2
            fullName = definition.name.replace("_", " ").title()
            label = QLabel(fullName, attributeContainer)
            label.setObjectName("playerAttributeLabel")
            editor = QSpinBox(attributeContainer)
            editor.setObjectName("playerAttributeInput")
            editor.setRange(0, 20)
            editor.setSpecialValueText("Unknown")
            editor.setValue(values.get(definition.name) or 0)
            editor.setToolTip(fullName)
            editor.setMinimumWidth(88)
            self.attributeInputs[definition.name] = editor
            attributeLayout.addWidget(label, row, column)
            attributeLayout.addWidget(editor, row, column + 1)
        scroll.setWidget(attributeContainer)

        attributesGroup = QGroupBox("Attributes", self)
        attributesGroup.setObjectName("playerEditorSection")
        attributesLayout = QVBoxLayout(attributesGroup)
        attributesLayout.setContentsMargins(8, 12, 8, 8)
        attributesLayout.addWidget(scroll)
        layout.addWidget(attributesGroup, 1)

        traitsGroup = QGroupBox("Known Traits", self)
        traitsGroup.setObjectName("playerEditorSection")
        traitsLayout = QVBoxLayout(traitsGroup)
        traitsLayout.setContentsMargins(12, 14, 12, 10)
        traitsLayout.setSpacing(8)
        self.traitsSummary = QLabel(traitsGroup)
        self.traitsSummary.setObjectName("playerTraitsSummary")
        self.traitsSummary.setWordWrap(True)
        traitsLayout.addWidget(self.traitsSummary)
        editTraits = QPushButton("Edit Known Traits", traitsGroup)
        editTraits.setObjectName("secondaryButton")
        editTraits.clicked.connect(self._traitsEdit)
        row = QHBoxLayout()
        row.addWidget(editTraits)
        row.addStretch()
        traitsLayout.addLayout(row)
        self._traitsSummaryUpdate()
        layout.addWidget(traitsGroup)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.setObjectName("playerEditorButtons")
        saveButton = buttons.button(QDialogButtonBox.StandardButton.Save)
        cancelButton = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        saveButton.setText("Save Player")
        saveButton.setObjectName("primaryButton")
        cancelButton.setObjectName("secondaryButton")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def editedPlayer(self) -> SquadModelPlayer:
        """Return validated factual edits while retaining immutable provenance fields."""

        name = playerNameStorage(self.nameInput.text().strip())
        if not name:
            raise ValueError("Player name is required")
        values = dict(self.player.attributes)
        for attributeName, editor in self.attributeInputs.items():
            values[attributeName] = editor.value() if editor.value() > 0 else None
        return replace(
            self.player,
            name=name,
            positions=self.positionsInput.text().strip(),
            ca=self.caInput.text().strip(),
            pa=self.paInput.text().strip(),
            validationState="corrected",
            attributes=tuple(sorted(values.items())),
            traits=self.selectedTraits,
        )

    def _attributeDefinitions(
        self,
        values: dict[str, int | None],
    ) -> tuple[AttributeDefinition, ...]:
        configured = {definition.name: definition for definition in self.attributes}
        definitions = list(self.attributes)
        nextOrder = max((definition.order for definition in definitions), default=0) + 1
        for name in sorted(set(values).difference(configured)):
            definitions.append(
                AttributeDefinition(
                    name=name,
                    abbreviation=name[:3].title(),
                    order=nextOrder,
                )
            )
            nextOrder += 1
        return tuple(sorted(definitions, key=lambda definition: definition.order))

    def _traitsEdit(self) -> None:
        dialog = PlayerTraitDialog(self.selectedTraits, self)
        dialog.setObjectName("playerTraitDialog")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selectedTraits = dialog.selectedTraits()
            self._traitsSummaryUpdate()

    def _traitsSummaryUpdate(self) -> None:
        self.traitsSummary.setText(
            "; ".join(self.selectedTraits) if self.selectedTraits else "No known traits"
        )
