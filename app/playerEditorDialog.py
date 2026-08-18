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

from fmsat.app.presentation import playerNameDisplay, playerNameStorage
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
        self.resize(880, 720)
        self.setMinimumSize(760, 620)

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
        provenance = (
            f"{player.validationState.title()}"
            + (
                f" · source import {player.sourceImportSessionId}"
                if player.sourceImportSessionId is not None
                else ""
            )
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
        attributeLayout.setContentsMargins(10, 10, 10, 10)
        attributeLayout.setHorizontalSpacing(10)
        attributeLayout.setVerticalSpacing(7)
        values = dict(player.attributes)
        definitions = self._attributeDefinitions(values)
        for index, definition in enumerate(definitions):
            row = index // 4
            column = (index % 4) * 2
            label = QLabel(definition.abbreviation, attributeContainer)
            label.setObjectName("playerAttributeLabel")
            label.setToolTip(definition.name.replace("_", " ").title())
            editor = QSpinBox(attributeContainer)
            editor.setObjectName("playerAttributeInput")
            editor.setRange(0, 20)
            editor.setSpecialValueText("Unknown")
            editor.setValue(values.get(definition.name) or 0)
            editor.setToolTip(definition.name.replace("_", " ").title())
            editor.setMinimumWidth(84)
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
        attributes = tuple(
            (name, editor.value() if editor.value() > 0 else None)
            for name, editor in sorted(self.attributeInputs.items())
        )
        return replace(
            self.player,
            name=name,
            positions=self.positionsInput.text().strip(),
            ca=self.caInput.text().strip(),
            pa=self.paInput.text().strip(),
            validationState="corrected",
            attributes=attributes,
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
