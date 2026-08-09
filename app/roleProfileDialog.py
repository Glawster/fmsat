"""Review dialog for screenshot-derived Football Manager role knowledge."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.colourPalette import cellHeader, cellHeaderText
from fmsat.core.config import AttributeDefinition
from fmsat.core.parser import RoleProfileEvidence, TacticalPhase
from fmsat.core.roleKnowledge import RoleKnowledgeError, RoleKnowledgeService


class RoleProfileReviewDialog(QDialog):
    """Review factual role evidence and confirm it through the core service."""

    def __init__(
        self,
        evidence: RoleProfileEvidence,
        expectedPosition: str,
        expectedRole: str,
        service: RoleKnowledgeService,
        parent=None,
        *,
        replaceExisting: bool = False,
        supportedPositions: tuple[str, ...] = (),
        attributeWeights: dict[str, int] | None = None,
        attributeImportance: dict[str, str] | None = None,
        attributeDefinitions: tuple[AttributeDefinition, ...] = (),
        phases: tuple[TacticalPhase, ...] = (),
    ) -> None:
        super().__init__(parent)
        self.evidence = evidence
        self.expectedPosition = expectedPosition
        self.expectedRole = expectedRole
        self.service = service
        self.replaceExisting = replaceExisting
        self.savedPath: Path | None = None
        self.setWindowTitle("Review Role Profile")
        self.resize(620, 760)
        layout = QVBoxLayout(self)
        expectedRoleLabel = expectedRole or "New role"
        layout.addWidget(QLabel(f"Expected: {expectedPosition} / {expectedRoleLabel}"))
        form = QFormLayout()
        phaseWidget = QWidget()
        phaseLayout = QHBoxLayout(phaseWidget)
        phaseLayout.setContentsMargins(0, 0, 0, 0)
        self.phaseGroup = QButtonGroup(self)
        self.inPossessionRadio = QRadioButton("In Possession")
        self.outOfPossessionRadio = QRadioButton("Out of Possession")
        self.bothPhasesRadio = QRadioButton("Both")
        for button in (
            self.inPossessionRadio,
            self.outOfPossessionRadio,
            self.bothPhasesRadio,
        ):
            self.phaseGroup.addButton(button)
            phaseLayout.addWidget(button)
        selectedPhases = phases or ((evidence.phase,) if evidence.phase is not None else ())
        if len(selectedPhases) == 2:
            self.bothPhasesRadio.setChecked(True)
        elif TacticalPhase.IN_POSSESSION in selectedPhases:
            self.inPossessionRadio.setChecked(True)
        elif TacticalPhase.OUT_OF_POSSESSION in selectedPhases:
            self.outOfPossessionRadio.setChecked(True)
        form.addRow("Phase", phaseWidget)
        self.positionEdit = QLineEdit(evidence.position)
        role = service.vocabulary.roles.get(expectedRole)
        initialPositions = (
            supportedPositions
            if supportedPositions
            else role.positions if role is not None else (expectedPosition,)
        )
        self.positionsEdit = QLineEdit(", ".join(initialPositions))
        self.roleEdit = QLineEdit(evidence.roleName)
        self.abbreviationEdit = QLineEdit(evidence.abbreviation or "")
        self.descriptionEdit = QPlainTextEdit(evidence.description or "")
        self.descriptionEdit.setFixedHeight(
            self.descriptionEdit.fontMetrics().lineSpacing() * 6 + 16
        )
        self.behavioursEdit = QLineEdit(", ".join(evidence.behaviours))
        form.addRow("Detected position", self.positionEdit)
        form.addRow("Supported positions", self.positionsEdit)
        form.addRow("Detected role", self.roleEdit)
        form.addRow("Abbreviation", self.abbreviationEdit)
        form.addRow("Description", self.descriptionEdit)
        form.addRow("Behaviours", self.behavioursEdit)
        layout.addLayout(form)
        importance = attributeImportance or {}
        definitions = {definition.name: definition for definition in attributeDefinitions} # type: ignore
        groupOrder = {"topThree": 0, "important": 1, "niceToHave": 2}
        attributes = sorted( # type: ignore
            evidence.keyAttributes,
            key=lambda attribute: (
                groupOrder.get(importance.get(attribute, ""), 3),
                definitions[attribute].order if attribute in definitions else 999,
                attribute,
            ),
        )
        self.attributeTable = QTableWidget(len(attributes), 4)
        self.attributeTable.setHorizontalHeaderLabels(
            ("Attribute", "Captured Value", "Weight (0–5)", "Importance")
        )
        self.attributeTable.setShowGrid(True)
        self.attributeTable.setAlternatingRowColors(True)
        self.attributeTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.attributeTable.setStyleSheet(
            "QTableWidget { gridline-color: #64748b; border: 1px solid #475569; }"
            "QHeaderView::section { font-weight: 700; border: 1px solid #64748b; "
            f"padding: 5px; background-color: {cellHeader}; color: {cellHeaderText}; }}"
            f"QTableWidget::item:selected {{ background-color: {cellHeader}; "
            f"color: {cellHeaderText}; }}"
        )
        weights = attributeWeights or {}
        for row, attribute in enumerate(attributes):
            nameItem = QTableWidgetItem(attribute.replace("_", " ").title())
            nameItem.setData(Qt.ItemDataRole.UserRole, attribute)
            self.attributeTable.setItem(row, 0, nameItem)
            value = evidence.displayedPlayerAttributes.get(attribute)
            self.attributeTable.setItem(
                row, 1, QTableWidgetItem("" if value is None else str(value))
            )
            weight = weights.get(attribute)
            self.attributeTable.setItem(
                row, 2, QTableWidgetItem("" if weight is None else str(weight))
            )
            importanceCombo = QComboBox()
            importanceCombo.addItem("Unassigned", "")
            importanceCombo.addItem("Top three", "topThree")
            importanceCombo.addItem("Important", "important")
            importanceCombo.addItem("Nice to have", "niceToHave")
            importanceCombo.setCurrentIndex(importanceCombo.findData(importance.get(attribute, "")))
            self.attributeTable.setCellWidget(row, 3, importanceCombo)
        layout.addWidget(self.attributeTable)
        self.instructionsEdit = QLineEdit(", ".join(evidence.playerInstructions))
        form.addRow("Player instructions", self.instructionsEdit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._definitionConfirm)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _definitionConfirm(self) -> None:
        attributes = []
        values = {}
        for row in range(self.attributeTable.rowCount()):
            nameItem = self.attributeTable.item(row, 0)
            attribute = str(nameItem.data(Qt.ItemDataRole.UserRole) or "").strip()
            if not attribute:
                continue
            attributes.append(attribute)
            value = self.attributeTable.item(row, 1).text().strip()
            if value.isdigit():
                values[attribute] = int(value)
        phases = self._phasesSelected()
        reviewedValues = dict(
            position=self.positionEdit.text().strip(),
            roleName=self.roleEdit.text().strip(),
            abbreviation=self.abbreviationEdit.text().strip() or None,
            description=self.descriptionEdit.toPlainText().strip() or None,
            behaviours=tuple(
                value.strip() for value in self.behavioursEdit.text().split(",") if value.strip()
            ),
            keyAttributes=tuple(attributes),
            playerInstructions=tuple(
                value.strip() for value in self.instructionsEdit.text().split(",") if value.strip()
            ),
            displayedPlayerAttributes=values,
            suitabilityStars=self.evidence.suitabilityStars,
            sourceImport=self.evidence.sourceImport,
            confidence=self.evidence.confidence,
        )
        try:
            if not phases:
                raise RoleKnowledgeError("Select a phase before saving")
            weights = {}
            importance = {}
            for row, attribute in enumerate(attributes):
                value = self.attributeTable.item(row, 2).text().strip()
                if value:
                    if not value.isdigit():
                        raise RoleKnowledgeError(f"Weight for {attribute} must be an integer")
                    weights[attribute] = int(value)
                importanceCombo = self.attributeTable.cellWidget(row, 3)
                group = importanceCombo.currentData()
                if group:
                    importance[attribute] = str(group)
            for phase in phases:
                reviewed = RoleProfileEvidence(phase=phase, **reviewedValues)
                draft = self.service.evidenceVerify(
                    reviewed,
                    self.expectedPosition,
                    self.expectedRole,
                    adoptDetectedRole=True,
                    supportedPositions=tuple(
                        value.strip()
                        for value in self.positionsEdit.text().split(",")
                        if value.strip()
                    ),
                )
                self.savedPath = self.service.definitionConfirm(
                    draft,
                    replace=self.replaceExisting,
                )
            self.service.weightsConfirm(draft.roleID, weights, importance)
        except (RoleKnowledgeError, ValueError) as exc:
            QMessageBox.warning(self, "Role profile needs review", str(exc))
            return
        self.accept()

    def _phasesSelected(self) -> tuple[TacticalPhase, ...]:
        if self.bothPhasesRadio.isChecked():
            return (TacticalPhase.IN_POSSESSION, TacticalPhase.OUT_OF_POSSESSION)
        if self.inPossessionRadio.isChecked():
            return (TacticalPhase.IN_POSSESSION,)
        if self.outOfPossessionRadio.isChecked():
            return (TacticalPhase.OUT_OF_POSSESSION,)
        return ()
