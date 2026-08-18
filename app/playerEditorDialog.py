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
        self.setWindowTitle(f"Edit Player · {playerNameDisplay(player.name)}")
        self.resize(820, 720)

        layout = QVBoxLayout(self)
        context = QLabel(
            "Edit factual player-model evidence here. Generic Role Fit, role depth and squad "
            "findings are derived automatically after the player is saved."
        )
        context.setObjectName("mutedText")
        context.setWordWrap(True)
        layout.addWidget(context)

        identityGroup = QGroupBox("Player", self)
        identity = QFormLayout(identityGroup)
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
        identity.addRow("Evidence status", QLabel(provenance, identityGroup))
        layout.addWidget(identityGroup)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        attributeContainer = QWidget(scroll)
        attributeLayout = QGridLayout(attributeContainer)
        values = dict(player.attributes)
        definitions = self._attributeDefinitions(values)
        for index, definition in enumerate(definitions):
            row = index // 4
            column = (index % 4) * 2
            label = QLabel(definition.abbreviation, attributeContainer)
            label.setToolTip(definition.name.replace("_", " ").title())
            editor = QSpinBox(attributeContainer)
            editor.setRange(0, 20)
            editor.setSpecialValueText("Unknown")
            editor.setValue(values.get(definition.name) or 0)
            editor.setToolTip(definition.name.replace("_", " ").title())
            self.attributeInputs[definition.name] = editor
            attributeLayout.addWidget(label, row, column)
            attributeLayout.addWidget(editor, row, column + 1)
        scroll.setWidget(attributeContainer)

        attributesGroup = QGroupBox("Attributes", self)
        attributesLayout = QVBoxLayout(attributesGroup)
        attributesLayout.addWidget(scroll)
        layout.addWidget(attributesGroup, 1)

        traitsGroup = QGroupBox("Known Traits", self)
        traitsLayout = QVBoxLayout(traitsGroup)
        self.traitsSummary = QLabel(traitsGroup)
        self.traitsSummary.setWordWrap(True)
        traitsLayout.addWidget(self.traitsSummary)
        editTraits = QPushButton("Edit Known Traits", traitsGroup)
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
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Save Player")
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
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selectedTraits = dialog.selectedTraits()
            self._traitsSummaryUpdate()

    def _traitsSummaryUpdate(self) -> None:
        self.traitsSummary.setText(
            "; ".join(self.selectedTraits) if self.selectedTraits else "No known traits"
        )
