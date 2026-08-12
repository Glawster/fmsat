"""Review dialog for screenshot-derived Football Manager role knowledge."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
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
        existingRoleID: int | None = None,
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
        self.existingRoleID = existingRoleID
        self.replaceExisting = replaceExisting
        self.savedPath: Path | None = None
        self.deletedPaths: tuple[Path, ...] = ()
        self.profileDeleted = False
        self.attributeDefinitions = attributeDefinitions
        self.attributeOrder = {
            definition.name: definition.order for definition in attributeDefinitions
        }
        self._attributeTableRefreshing = False
        self.setWindowTitle("Review Role Profile")
        self.resize(620, 760)
        layout = QVBoxLayout(self)
        headerButtons = QHBoxLayout()
        headerButtons.addStretch()
        self.deleteProfileButton = QPushButton("Delete this profile card")
        self.deleteProfileButton.setObjectName("deleteProfileButton")
        self.deleteProfileButton.setEnabled(self.existingRoleID is not None)
        self.deleteProfileButton.clicked.connect(self._profileDelete)
        headerButtons.addWidget(self.deleteProfileButton)
        layout.addLayout(headerButtons)
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
        attributes = list(evidence.keyAttributes)
        self.attributeTable = QTableWidget(len(attributes), 4)
        self.attributeTable.setHorizontalHeaderLabels(
            ("Attribute", "Captured Value", "Weight (0–5)", "Importance")
        )
        self.attributeTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.attributeTable.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.SelectedClicked
            | QTableWidget.EditTrigger.AnyKeyPressed
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
            rowData = {
                "attribute": attribute,
                "label": attribute.replace("_", " ").title(),
                "value": "" if evidence.displayedPlayerAttributes.get(attribute) is None else str(evidence.displayedPlayerAttributes.get(attribute)),
                "weight": "" if weights.get(attribute) is None else str(weights.get(attribute)),
                "importance": "topThree" if row < 3 else importance.get(attribute, ""),
            }
            self._attributeRowWrite(row, rowData)
        layout.addWidget(self.attributeTable)
        self.attributeTable.itemSelectionChanged.connect(self._attributeButtonsRefresh)
        attributeButtons = QHBoxLayout()
        self.moveAttributeUpButton = QPushButton("↑")
        self.moveAttributeUpButton.setObjectName("moveAttributeUpButton")
        self.moveAttributeUpButton.clicked.connect(lambda: self._attributeMove(-1))
        attributeButtons.addWidget(self.moveAttributeUpButton)
        self.moveAttributeDownButton = QPushButton("↓")
        self.moveAttributeDownButton.setObjectName("moveAttributeDownButton")
        self.moveAttributeDownButton.clicked.connect(lambda: self._attributeMove(1))
        attributeButtons.addWidget(self.moveAttributeDownButton)
        attributeButtons.addStretch()
        addButton = QPushButton("Add Attribute")
        addButton.setObjectName("addAttributeButton")
        addButton.clicked.connect(self._attributeRowAdd)
        attributeButtons.addWidget(addButton)
        self.deleteAttributeButton = QPushButton("Delete Attribute")
        self.deleteAttributeButton.setObjectName("deleteAttributeButton")
        self.deleteAttributeButton.clicked.connect(self._attributeRowDelete)
        attributeButtons.addWidget(self.deleteAttributeButton)
        layout.addLayout(attributeButtons)
        self._attributeButtonsRefresh()
        self.instructionsEdit = QLineEdit(", ".join(evidence.playerInstructions))
        form.addRow("Player instructions", self.instructionsEdit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._definitionConfirm)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _attributeRowAdd(self) -> None:
        row = self.attributeTable.rowCount()
        self.attributeTable.setRowCount(row + 1)
        self._attributeRowWrite(
            row,
            {
                "attribute": "",
                "label": "",
                "value": "",
                "weight": "",
                "importance": "",
            },
        )
        self.attributeTable.setCurrentCell(row, 0)
        self._attributeButtonsRefresh()

    def _attributeImportanceChanged(self) -> None:
        if self._attributeTableRefreshing:
            return
        combo = self.sender()
        selectedAttribute = ""
        if isinstance(combo, QComboBox):
            selectedAttribute = str(combo.property("attributeKey") or "")
            if not selectedAttribute:
                selectedAttribute = str(combo.property("attributeLabel") or "")
        self._attributeRowsRebuild(selectedAttribute)

    def _attributeButtonsRefresh(self) -> None:
        currentRow = self.attributeTable.currentRow()
        hasSelection = currentRow >= 0
        self.deleteAttributeButton.setEnabled(hasSelection)
        self.moveAttributeUpButton.setEnabled(hasSelection and currentRow > 0)
        self.moveAttributeDownButton.setEnabled(
            hasSelection and currentRow < self.attributeTable.rowCount() - 1
        )

    def _attributeRowDelete(self) -> None:
        row = self.attributeTable.currentRow()
        if row < 0:
            return
        self.attributeTable.removeRow(row)
        if self.attributeTable.rowCount() > 0:
            self.attributeTable.setCurrentCell(min(row, self.attributeTable.rowCount() - 1), 0)
        self._attributeButtonsRefresh()

    def _attributeOrderKey(self, rowData: dict[str, str]) -> tuple[int, object, str]:
        groupOrder = {"topThree": 0, "important": 1, "niceToHave": 2}
        return (
            groupOrder.get(rowData["importance"], 3),
            int(rowData.get("orderIndex", "0")),
        )

    def _attributeRowRead(self, row: int) -> dict[str, str]:
        nameItem = self.attributeTable.item(row, 0)
        valueItem = self.attributeTable.item(row, 1)
        weightItem = self.attributeTable.item(row, 2)
        importanceCombo = self.attributeTable.cellWidget(row, 3)
        return {
            "attribute": str(nameItem.data(Qt.ItemDataRole.UserRole) or "").strip() if nameItem is not None else "",
            "label": nameItem.text().strip() if nameItem is not None else "",
            "value": valueItem.text().strip() if valueItem is not None else "",
            "weight": weightItem.text().strip() if weightItem is not None else "",
            "importance": str(importanceCombo.currentData() or "") if isinstance(importanceCombo, QComboBox) else "",
        }

    def _attributeMove(self, offset: int) -> None:
        row = self.attributeTable.currentRow()
        if row < 0:
            return
        targetRow = row + offset
        if targetRow < 0 or targetRow >= self.attributeTable.rowCount():
            return
        rows = [self._attributeRowRead(index) for index in range(self.attributeTable.rowCount())]
        rows[row], rows[targetRow] = rows[targetRow], rows[row]
        self._attributeTopThreeNormalize(rows)
        selectedAttribute = rows[targetRow]["attribute"] or rows[targetRow]["label"]
        self._attributeRowsWrite(rows, selectedAttribute)

    def _attributeRowsRebuild(self, selectedAttribute: str = "") -> None:
        rows = [self._attributeRowRead(row) for row in range(self.attributeTable.rowCount())]
        for index, rowData in enumerate(rows):
            rowData["orderIndex"] = str(index)
        rows.sort(key=self._attributeOrderKey)
        self._attributeTopThreeLimit(rows)
        self._attributeRowsWrite(rows, selectedAttribute)

    def _attributeRowsWrite(self, rows: list[dict[str, str]], selectedAttribute: str = "") -> None:
        for index, rowData in enumerate(rows):
            rowData["orderIndex"] = str(index)

        self._attributeTableRefreshing = True
        self.attributeTable.setRowCount(len(rows))
        for row, rowData in enumerate(rows):
            self._attributeRowWrite(row, rowData)
        self._attributeTableRefreshing = False

        if rows:
            selectedRow = 0
            if selectedAttribute:
                for row, rowData in enumerate(rows):
                    attributeKey = rowData["attribute"] or self._attributeKeyResolve(rowData["label"])
                    if attributeKey == selectedAttribute or rowData["label"] == selectedAttribute:
                        selectedRow = row
                        break
            self.attributeTable.setCurrentCell(selectedRow, 0)
        self._attributeButtonsRefresh()

    @staticmethod
    def _attributeTopThreeLimit(rows: list[dict[str, str]]) -> None:
        topThreeRows = [rowData for rowData in rows if rowData["importance"] == "topThree"]
        while len(topThreeRows) > 3:
            demoted = topThreeRows.pop()
            demoted["importance"] = "important"

    @classmethod
    def _attributeTopThreeNormalize(cls, rows: list[dict[str, str]]) -> None:
        for index, rowData in enumerate(rows):
            if index < 3:
                rowData["importance"] = "topThree"
            elif rowData["importance"] == "topThree":
                rowData["importance"] = "important"
        cls._attributeTopThreeLimit(rows)

    def _attributeRowWrite(self, row: int, rowData: dict[str, str]) -> None:
        nameItem = QTableWidgetItem(rowData["label"])
        nameItem.setData(Qt.ItemDataRole.UserRole, rowData["attribute"])
        nameItem.setFlags(nameItem.flags() | Qt.ItemFlag.ItemIsEditable)
        self.attributeTable.setItem(row, 0, nameItem)
        self.attributeTable.setItem(row, 1, QTableWidgetItem(rowData["value"]))
        self.attributeTable.setItem(row, 2, QTableWidgetItem(rowData["weight"]))
        importanceCombo = QComboBox()
        importanceCombo.addItem("Unassigned", "")
        importanceCombo.addItem("Top three", "topThree")
        importanceCombo.addItem("Important", "important")
        importanceCombo.addItem("Nice to have", "niceToHave")
        importanceCombo.setProperty("attributeKey", rowData["attribute"])
        importanceCombo.setProperty("attributeLabel", rowData["label"])
        importanceCombo.setCurrentIndex(importanceCombo.findData(rowData["importance"]))
        importanceCombo.currentIndexChanged.connect(self._attributeImportanceChanged)
        self.attributeTable.setCellWidget(row, 3, importanceCombo)

    def _attributeKeyResolve(self, rawAttribute: str) -> str:
        """Map a visible attribute label back to the canonical stored attribute key."""

        normalizedText = re.sub(r"[^a-z0-9]+", "_", rawAttribute.strip().casefold()).strip("_")
        if not normalizedText:
            return ""

        knownAttributes = {attribute.casefold(): attribute for attribute in self.service.attributeIds}
        if normalizedText in knownAttributes:
            return knownAttributes[normalizedText]

        # Prefer configured attribute labels so typed display names like
        # "Off The Ball" map back to the expected storage key.
        definitionLookup: dict[str, str] = {}
        for definition in self.attributeDefinitions:
            definitionLookup[definition.name.casefold()] = definition.name
            displayName = definition.name.replace("_", " ")
            definitionLookup[displayName.casefold()] = definition.name
        return definitionLookup.get(rawAttribute.strip().casefold(), normalizedText)

    def _profileDelete(self) -> None:
        if self.existingRoleID is None:
            return
        result = QMessageBox.question(
            self,
            "Delete role profile",
            "Delete this saved role profile and its assessment data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        try:
            self.deletedPaths = self.service.definitionDelete(self.existingRoleID)
        except RoleKnowledgeError as exc:
            QMessageBox.warning(self, "Role profile needs review", str(exc))
            return
        self.profileDeleted = True
        self.accept()

    def _definitionConfirm(self) -> None:
        attributes = []
        values = {}
        for row in range(self.attributeTable.rowCount()):
            nameItem = self.attributeTable.item(row, 0)
            attribute = str(nameItem.data(Qt.ItemDataRole.UserRole) or "").strip()
            if not attribute:
                attribute = self._attributeKeyResolve(str(nameItem.text() or ""))
            if not attribute:
                continue
            attributes.append(attribute)
            valueItem = self.attributeTable.item(row, 1)
            valueText = valueItem.text().strip() if valueItem is not None else ""
            if valueText.isdigit():
                values[attribute] = int(valueText)
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
        supportedPositions = tuple(
            value.strip() for value in self.positionsEdit.text().split(",") if value.strip()
        )
        expectedPosition = self.expectedPosition
        detectedPosition = reviewedValues["position"]
        normalizedDetectedPosition = self.service.vocabulary.positionNormalize(detectedPosition)
        if (
            normalizedDetectedPosition.resolved
            and normalizedDetectedPosition.value != self.expectedPosition
        ):
            expectedPosition = self._expectedPositionResolve(
                detectedPosition,
                normalizedDetectedPosition.value,
            )
            if not expectedPosition:
                return
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
                    expectedPosition,
                    self.expectedRole,
                    adoptDetectedRole=True,
                    supportedPositions=supportedPositions,
                )
                if self.existingRoleID is not None and not self.expectedRole:
                    draft = replace(draft, roleID=self.existingRoleID)
                self.savedPath = self.service.definitionConfirm(
                    draft,
                    replace=self.replaceExisting,
                )
            self.service.weightsConfirm(draft.roleID, weights, importance)
        except (RoleKnowledgeError, ValueError) as exc:
            QMessageBox.warning(self, "Role profile needs review", str(exc))
            return
        self.accept()

    def _expectedPositionResolve(self, detectedPosition: str, normalizedPosition: str) -> str | None:
        # Preserve strict verification by default, but let reviewers explicitly
        # continue when OCR and tactical expectation disagree.
        result = QMessageBox.question(
            self,
            "Role profile needs review",
            (
                f"Expected position {self.expectedPosition}, but the role profile shows "
                f"{detectedPosition or 'an unresolved position'}.\n\n"
                f"Continue and save this definition using {normalizedPosition}?"
            ),
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if result != QMessageBox.StandardButton.Ok:
            return None
        return normalizedPosition

    def _phasesSelected(self) -> tuple[TacticalPhase, ...]:
        if self.bothPhasesRadio.isChecked():
            return (TacticalPhase.IN_POSSESSION, TacticalPhase.OUT_OF_POSSESSION)
        if self.inPossessionRadio.isChecked():
            return (TacticalPhase.IN_POSSESSION,)
        if self.outOfPossessionRadio.isChecked():
            return (TacticalPhase.OUT_OF_POSSESSION,)
        return ()
