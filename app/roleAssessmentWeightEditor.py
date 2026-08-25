"""Bulk editor for the packaged Generic Role Fit assessment policy."""

from __future__ import annotations

from pathlib import Path

import yaml
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.adminWidgets import AdminEditDialog, adminTableConfigure
from fmsat.core.roleAssessmentPolicy import (
    RoleAssessmentPolicyError,
    RoleAssessmentPolicyService,
)


class RoleAssessmentWeightEditor(AdminEditDialog):
    """Edit all role weights in one place and import/export them as YAML."""

    def __init__(
        self,
        service: RoleAssessmentPolicyService,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Role Assessment Weights")

        layout = QVBoxLayout(self)
        title = QLabel(
            "Generic Role Fit assessment policy — weights use the 0–10 scale.",
            self,
        )
        layout.addWidget(title)

        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(("Role code", "Attribute", "Weight (0–10)"))
        adminTableConfigure(self.table, compactColumns=(2,))
        layout.addWidget(self.table, 1)

        controls = QHBoxLayout()
        self.importButton = QPushButton("Import YAML", self)
        self.exportButton = QPushButton("Export YAML", self)
        self.saveButton = QPushButton("Save", self)
        self.closeButton = QPushButton("Close", self)
        controls.addWidget(self.importButton)
        controls.addWidget(self.exportButton)
        controls.addStretch(1)
        controls.addWidget(self.saveButton)
        controls.addWidget(self.closeButton)
        layout.addLayout(controls)

        self.importButton.clicked.connect(self._import)
        self.exportButton.clicked.connect(self._export)
        self.saveButton.clicked.connect(self._save)
        self.closeButton.clicked.connect(self.accept)
        self._loadCurrent()

    def _loadCurrent(self) -> None:
        try:
            data = yaml.safe_load(self.service.policyPath.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            QMessageBox.critical(self, "Role weights unavailable", str(exc))
            return
        roles = data.get("roles") if isinstance(data, dict) else None
        if not isinstance(roles, dict):
            return
        rows = [
            (str(roleCode), str(attribute), int(weight))
            for roleCode, roleData in roles.items()
            if isinstance(roleData, dict)
            for attribute, weight in (roleData.get("attributeWeights") or {}).items()
            if isinstance(weight, int)
        ]
        self.table.setRowCount(len(rows))
        for row, (roleCode, attribute, weight) in enumerate(rows):
            roleItem = QTableWidgetItem(roleCode)
            roleItem.setFlags(roleItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
            attributeItem = QTableWidgetItem(attribute)
            attributeItem.setFlags(attributeItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, roleItem)
            self.table.setItem(row, 1, attributeItem)
            editor = QSpinBox(self.table)
            editor.setRange(0, 10)
            editor.setValue(weight)
            self.table.setCellWidget(row, 2, editor)

    def _save(self) -> None:
        try:
            data = yaml.safe_load(self.service.policyPath.read_text(encoding="utf-8")) or {}
            roles = data.get("roles")
            if not isinstance(roles, dict):
                raise RoleAssessmentPolicyError("Current policy has no roles mapping")
            for row in range(self.table.rowCount()):
                roleCode = self.table.item(row, 0).text()
                attribute = self.table.item(row, 1).text()
                editor = self.table.cellWidget(row, 2)
                if not isinstance(editor, QSpinBox):
                    continue
                roleData = roles.get(roleCode)
                if isinstance(roleData, dict) and isinstance(roleData.get("attributeWeights"), dict):
                    roleData["attributeWeights"][attribute] = editor.value()
            temporary = self.service.policyPath.with_suffix(".editor.yaml")
            temporary.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            self.service.importFile(temporary)
            temporary.unlink(missing_ok=True)
        except (OSError, yaml.YAMLError, RoleAssessmentPolicyError) as exc:
            QMessageBox.critical(self, "Unable to save role weights", str(exc))
            return
        QMessageBox.information(self, "Role weights saved", "Assessment weights were saved successfully.")

    def _import(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Import Role Assessment Weights", "", "YAML (*.yaml *.yml)")
        if not filename:
            return
        try:
            preview = self.service.preview(Path(filename))
        except RoleAssessmentPolicyError as exc:
            QMessageBox.critical(self, "Invalid role weights", str(exc))
            return
        migration = " Legacy 0–5 weights will be converted to 0–10." if preview.migratedLegacyScale else ""
        answer = QMessageBox.question(
            self,
            "Apply role weights?",
            f"Validated {preview.roleCount} roles and {preview.attributeCount} weights.{migration}\n\nReplace the current assessment policy?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.importFile(Path(filename))
        except RoleAssessmentPolicyError as exc:
            QMessageBox.critical(self, "Unable to import role weights", str(exc))
            return
        self._loadCurrent()

    def _export(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "Export Role Assessment Weights", "roleAssessment.yaml", "YAML (*.yaml *.yml)")
        if not filename:
            return
        try:
            self.service.exportFile(Path(filename))
        except RoleAssessmentPolicyError as exc:
            QMessageBox.critical(self, "Unable to export role weights", str(exc))
