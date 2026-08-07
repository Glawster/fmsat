"""Review dialog for screenshot-derived Football Manager role knowledge."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from fmsat.core.parser import RoleProfileEvidence
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
    ) -> None:
        super().__init__(parent)
        self.evidence = evidence
        self.expectedPosition = expectedPosition
        self.expectedRole = expectedRole
        self.service = service
        self.replaceExisting = replaceExisting
        self.savedPath: Path | None = None
        self.setWindowTitle("Review Role Profile")
        self.resize(620, 560)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Expected: {expectedPosition} / {expectedRole}"))
        phase = evidence.phase.value if evidence.phase is not None else "Unresolved"
        layout.addWidget(QLabel(f"Detected phase: {phase}"))
        form = QFormLayout()
        self.positionEdit = QLineEdit(evidence.position)
        self.roleEdit = QLineEdit(evidence.roleName)
        self.abbreviationEdit = QLineEdit(evidence.abbreviation or "")
        self.descriptionEdit = QPlainTextEdit(evidence.description or "")
        form.addRow("Detected position", self.positionEdit)
        form.addRow("Detected role", self.roleEdit)
        form.addRow("Abbreviation", self.abbreviationEdit)
        form.addRow("Description", self.descriptionEdit)
        layout.addLayout(form)
        self.attributeTable = QTableWidget(len(evidence.keyAttributes), 2)
        self.attributeTable.setHorizontalHeaderLabels(("Key attribute", "Displayed value"))
        for row, attribute in enumerate(evidence.keyAttributes):
            self.attributeTable.setItem(row, 0, QTableWidgetItem(attribute))
            value = evidence.displayedPlayerAttributes.get(attribute)
            self.attributeTable.setItem(
                row, 1, QTableWidgetItem("" if value is None else str(value))
            )
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
            attribute = self.attributeTable.item(row, 0).text().strip()
            if not attribute:
                continue
            attributes.append(attribute)
            value = self.attributeTable.item(row, 1).text().strip()
            if value.isdigit():
                values[attribute] = int(value)
        reviewed = RoleProfileEvidence(
            position=self.positionEdit.text().strip(),
            roleName=self.roleEdit.text().strip(),
            phase=self.evidence.phase,
            abbreviation=self.abbreviationEdit.text().strip() or None,
            description=self.descriptionEdit.toPlainText().strip() or None,
            behaviours=self.evidence.behaviours,
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
            draft = self.service.evidenceVerify(
                reviewed,
                self.expectedPosition,
                self.expectedRole,
                adoptDetectedRole=True,
            )
            self.savedPath = self.service.definitionConfirm(
                draft,
                replace=self.replaceExisting,
            )
        except (RoleKnowledgeError, ValueError) as exc:
            QMessageBox.warning(self, "Role profile needs review", str(exc))
            return
        self.accept()
