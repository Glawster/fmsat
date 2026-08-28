"""Matrix view for Generic Role Fit weights and attribute activation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import yaml
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionHeader,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.colourPalette import BUTTON_SELECTED
from fmsat.app.presentation import attributeIsGoalkeeperOnly, rolePositionSortKey
from fmsat.app.styles import stylePaletteLoad
from fmsat.core.config import (
    AttributeConfigurationService,
    AttributeDefinition,
    ConfigurationError,
)
from fmsat.core.roleAssessmentPolicy import (
    RoleAssessmentPolicyError,
    RoleAssessmentPolicyService,
)

_activeDataRole = int(Qt.ItemDataRole.UserRole) + 1


class _WeightMatrixDelegate(QStyledItemDelegate):
    """Paint matrix text explicitly so QSS cannot override semantic colours."""

    def __init__(self, paletteColours: Mapping[str, str], parent: QWidget) -> None:
        super().__init__(parent)
        self.paletteColours = paletteColours
        self.importanceColours = {
            "topThree": QColor(paletteColours["successText"]),
            "important": QColor(BUTTON_SELECTED),
            "niceToHave": QColor(paletteColours["neutralText"]),
        }

    def textColour(self, active: bool | None, importance: str) -> QColor:
        """Return the rendered text colour for one matrix value."""

        if active is False:
            return QColor(self.paletteColours["inactiveText"])
        return self.importanceColours.get(
            importance,
            QColor(self.paletteColours["textPrimary"]),
        )

    def paint(self, painter, option, index) -> None:  # type: ignore[no-untyped-def]
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        text = styled.text
        styled.text = ""

        style = styled.widget.style() if styled.widget is not None else None
        if style is not None:
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, styled, painter, styled.widget)
        else:
            super().paint(painter, styled, index)

        if not text:
            return

        active = index.data(_activeDataRole)
        importance = str(index.data(Qt.ItemDataRole.UserRole) or "")
        painter.save()
        painter.setPen(self.textColour(active, importance))
        painter.setFont(styled.font)
        painter.drawText(styled.rect.adjusted(4, 0, -4, 0), styled.displayAlignment, text)
        painter.restore()


class _WeightHeaderView(QHeaderView):
    """Paint active/inactive attribute headings explicitly over the shared QSS."""

    def __init__(self, paletteColours: Mapping[str, str], parent: QWidget) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.paletteColours = paletteColours

    def paintSection(self, painter, rect, logicalIndex: int) -> None:  # type: ignore[no-untyped-def]
        if not rect.isValid():
            return

        option = QStyleOptionHeader()
        self.initStyleOption(option)
        option.rect = rect
        option.section = logicalIndex
        option.text = ""
        self.style().drawControl(QStyle.ControlElement.CE_Header, option, painter, self)

        model = self.model()
        if model is None:
            return
        text = str(
            model.headerData(
                logicalIndex,
                Qt.Orientation.Horizontal,
                Qt.ItemDataRole.DisplayRole,
            )
            or ""
        )
        if not text:
            return

        active = model.headerData(
            logicalIndex,
            Qt.Orientation.Horizontal,
            _activeDataRole,
        )
        colourKey = "inactiveText" if active is False else "textSecondary"
        font = QFont(self.font())
        font.setItalic(active is False)

        painter.save()
        painter.setPen(QColor(self.paletteColours[colourKey]))
        painter.setFont(font)
        painter.drawText(rect.adjusted(4, 0, -4, 0), Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()


class RoleAssessmentWeightEditor(QDialog):
    """Show role weights as an attribute matrix and route edits to the Role Editor."""

    def __init__(
        self,
        service: RoleAssessmentPolicyService,
        *,
        roles: Mapping[str, object] | None = None,
        attributes: tuple[AttributeDefinition, ...] = (),
        roleKnowledge: object | None = None,
        attributeService: AttributeConfigurationService | None = None,
        roleOpen: Callable[[str], None] | None = None,
        attributesChanged: Callable[[tuple[AttributeDefinition, ...]], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        # Do not inherit AdminEditDialog: that class owns the legacy light editor
        # palette. The weights matrix is an FMSAT view and inherits application QSS.
        super().__init__(parent)
        self.setObjectName("roleAssessmentWeightEditor")
        self.service = service
        self.roles = roles or {}
        self.attributes = attributes
        self.roleKnowledge = roleKnowledge
        self.attributeService = attributeService
        self.roleOpen = roleOpen
        self.attributesChanged = attributesChanged
        self.paletteColours = stylePaletteLoad()
        self.goalkeeperAttributesVisible = False
        self.setWindowTitle("Role Assessment Weights")
        self.setMinimumSize(900, 600)
        self.resize(1680, 860)

        layout = QVBoxLayout(self)
        title = QLabel(
            "Generic Role Fit assessment matrix — click an attribute heading to include or "
            "exclude it from FMSAT; click a role identifier to edit that role.",
            self,
        )
        title.setWordWrap(True)
        layout.addWidget(title)

        legend = QLabel(self)
        legend.setTextFormat(Qt.TextFormat.RichText)
        legend.setText(
            f'<span style="color:{self.paletteColours["successText"]}">Top Three = green</span>'
            ' &nbsp;·&nbsp; '
            f'<span style="color:{BUTTON_SELECTED}">Important = blue</span>'
            ' &nbsp;·&nbsp; '
            f'<span style="color:{self.paletteColours["neutralText"]}">Nice to Have = grey</span>'
            ' &nbsp;·&nbsp; '
            f'<span style="color:{self.paletteColours["inactiveText"]}">inactive attributes are muted</span>'
        )
        layout.addWidget(legend)

        self.table = QTableWidget(self)
        self.table.setObjectName("roleAssessmentWeightMatrix")
        self.table.setHorizontalHeader(_WeightHeaderView(self.paletteColours, self.table))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().sectionClicked.connect(self._attributeHeaderClicked)
        self.table.cellClicked.connect(self._cellClicked)
        self.table.setItemDelegate(_WeightMatrixDelegate(self.paletteColours, self.table))
        layout.addWidget(self.table, 1)

        controls = QHBoxLayout()
        self.importButton = QPushButton("Import YAML", self)
        self.exportButton = QPushButton("Export YAML", self)
        self.closeButton = QPushButton("Close", self)
        controls.addWidget(self.importButton)
        controls.addWidget(self.exportButton)
        controls.addStretch(1)
        controls.addWidget(self.closeButton)
        layout.addLayout(controls)

        self.importButton.clicked.connect(self._import)
        self.exportButton.clicked.connect(self._export)
        self.closeButton.clicked.connect(self.close)
        self._loadCurrent()

    def _policyRoles(self) -> dict[str, object]:
        try:
            data = yaml.safe_load(self.service.policyPath.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return {}
        roles = data.get("roles") if isinstance(data, dict) else None
        return dict(roles) if isinstance(roles, dict) else {}

    def _roleWeights(self, roleCode: str, packaged: dict[str, object]) -> dict[str, int]:
        weightsLoad = getattr(self.roleKnowledge, "weightsLoad", None)
        if callable(weightsLoad):
            loaded = weightsLoad(roleCode)
            if isinstance(loaded, dict) and loaded:
                return {str(name): int(value) for name, value in loaded.items()}
        roleData = packaged.get(roleCode)
        weights = roleData.get("attributeWeights") if isinstance(roleData, dict) else None
        if not isinstance(weights, dict):
            return {}
        return {str(name): int(value) for name, value in weights.items() if isinstance(value, int)}

    def _roleImportance(self, roleCode: str, weights: Mapping[str, int]) -> dict[str, str]:
        """Load confirmed ranking, falling back to deterministic packaged-policy tiers."""

        importanceLoad = getattr(self.roleKnowledge, "importanceLoad", None)
        if callable(importanceLoad):
            loaded = importanceLoad(roleCode)
            if isinstance(loaded, dict) and loaded:
                return {str(name): str(group) for name, group in loaded.items()}

        ranked = sorted(weights, key=lambda name: -weights[name])
        topThree = set(ranked[:3])
        return {
            name: (
                "topThree"
                if name in topThree
                else "important" if weight >= 8 else "niceToHave"
            )
            for name, weight in weights.items()
        }

    def _rolePresentation(self, roleCode: str) -> tuple[str, str, str]:
        role = self.roles.get(roleCode)
        displayName = str(getattr(role, "displayName", "") or roleCode)
        abbreviations = tuple(getattr(role, "abbreviations", ()) or ())
        abbreviation = str(abbreviations[0]) if abbreviations else roleCode
        return abbreviation, displayName, roleCode

    def _roleSortKey(self, roleCode: str) -> tuple[int, int, str, str]:
        role = self.roles.get(roleCode)
        if role is not None and hasattr(role, "positions"):
            return rolePositionSortKey(role)
        _abbreviation, displayName, semanticCode = self._rolePresentation(roleCode)
        return 7, 3, displayName.casefold(), semanticCode.casefold()

    def _roleIsGoalkeeper(self, roleCode: str) -> bool:
        role = self.roles.get(roleCode)
        positions = tuple(getattr(role, "positions", ()) or ())
        return any(str(position).strip().upper() == "GK" for position in positions)

    def _visibleAttributes(self) -> tuple[AttributeDefinition, ...]:
        if self.goalkeeperAttributesVisible:
            return self.attributes
        return tuple(
            attribute
            for attribute in self.attributes
            if not attributeIsGoalkeeperOnly(attribute.name)
        )

    def _loadCurrent(self) -> None:
        packaged = self._policyRoles()
        roleCodes = sorted(
            set(self.service.roleCodes) | set(packaged) | set(self.roles),
            key=self._roleSortKey,
        )
        visibleAttributes = self._visibleAttributes()
        self.table.clear()
        self.table.setRowCount(len(roleCodes))
        self.table.setColumnCount(len(visibleAttributes) + 1)
        self.table.setHorizontalHeaderLabels(
            ["Role", *(attribute.abbreviation for attribute in visibleAttributes)]
        )

        roleHeader = self.table.horizontalHeaderItem(0)
        if roleHeader is not None:
            roleHeader.setToolTip("Role identifier — click a role row to open the Role Editor")
            roleHeader.setData(_activeDataRole, True)

        for column, attribute in enumerate(visibleAttributes, start=1):
            header = self.table.horizontalHeaderItem(column)
            if header is not None:
                header.setData(Qt.ItemDataRole.UserRole, attribute.name)
                header.setData(_activeDataRole, attribute.active)
            self._attributeHeaderRender(column, attribute)

        for row, roleCode in enumerate(roleCodes):
            abbreviation, displayName, semanticCode = self._rolePresentation(roleCode)
            roleItem = QTableWidgetItem(abbreviation)
            roleItem.setData(Qt.ItemDataRole.UserRole, semanticCode)
            roleItem.setData(_activeDataRole, True)
            roleItem.setToolTip(
                f"{displayName}\n{semanticCode}\nClick to open this role in the Role Editor."
            )
            roleItem.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 0, roleItem)

            weights = self._roleWeights(roleCode, packaged)
            importance = self._roleImportance(roleCode, weights)
            for column, attribute in enumerate(visibleAttributes, start=1):
                value = weights.get(attribute.name)
                item = QTableWidgetItem("" if value is None else str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setData(Qt.ItemDataRole.UserRole, importance.get(attribute.name, ""))
                item.setData(_activeDataRole, attribute.active)
                item.setToolTip(
                    f"{displayName} · {attribute.name.replace('_', ' ').title()}\n"
                    + ("No assessment weight defined" if value is None else f"Weight {value}/10")
                )
                self.table.setItem(row, column, item)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 115)
        self.table.viewport().update()
        self.table.horizontalHeader().viewport().update()

    def _paletteBrush(self, key: str) -> QBrush:
        return QBrush(QColor(self.paletteColours[key]))

    def _attributeHeaderRender(self, column: int, attribute: AttributeDefinition) -> None:
        header = self.table.horizontalHeaderItem(column)
        if header is None:
            return
        state = "Active" if attribute.active else "Inactive"
        action = "exclude from" if attribute.active else "include in"
        header.setToolTip(
            f"{attribute.name.replace('_', ' ').title()} — {state}. "
            f"Click to {action} FMSAT. Stored role weights are retained."
        )
        header.setData(_activeDataRole, attribute.active)
        font = QFont(header.font())
        font.setItalic(not attribute.active)
        header.setFont(font)
        header.setForeground(
            self._paletteBrush("textSecondary" if attribute.active else "inactiveText")
        )

    def _attributeHeaderClicked(self, column: int) -> None:
        if column <= 0 or column >= self.table.columnCount():
            return
        header = self.table.horizontalHeaderItem(column)
        if header is None:
            return
        attributeName = str(header.data(Qt.ItemDataRole.UserRole) or "")
        attribute = next(
            (item for item in self.attributes if item.name == attributeName),
            None,
        )
        if attribute is None or self.attributeService is None:
            return
        try:
            updated = self.attributeService.activeSet(attribute.name, not attribute.active)
        except ConfigurationError as exc:
            QMessageBox.critical(self, "Unable to change attribute state", str(exc))
            return
        self.attributes = updated
        if self.attributesChanged is not None:
            self.attributesChanged(updated)
        self._loadCurrent()

    def _cellClicked(self, row: int, column: int) -> None:
        if column != 0 or self.roleOpen is None:
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        roleCode = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
        if not roleCode:
            return
        self.goalkeeperAttributesVisible = self._roleIsGoalkeeper(roleCode)
        self.roleOpen(roleCode)
        self._loadCurrent()

    def _defaultsRefresh(self) -> None:
        if self.roleKnowledge is None:
            return
        packaged = self._policyRoles()
        defaults: dict[str, dict[str, int]] = {}
        for roleCode, roleData in packaged.items():
            weights = roleData.get("attributeWeights") if isinstance(roleData, dict) else None
            if isinstance(weights, dict):
                defaults[str(roleCode)] = {
                    str(name): int(value)
                    for name, value in weights.items()
                    if isinstance(value, int)
                }
        if hasattr(self.roleKnowledge, "defaultWeights"):
            self.roleKnowledge.defaultWeights = defaults

    def _import(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Role Assessment Weights", "", "YAML (*.yaml *.yml)"
        )
        if not filename:
            return
        try:
            preview = self.service.preview(Path(filename))
        except RoleAssessmentPolicyError as exc:
            QMessageBox.critical(self, "Invalid role weights", str(exc))
            return
        migration = (
            " Legacy 0–5 weights will be converted to 0–10." if preview.migratedLegacyScale else ""
        )
        answer = QMessageBox.question(
            self,
            "Apply role weights?",
            f"Validated {preview.roleCount} roles and {preview.attributeCount} weights.{migration}"
            "\n\nReplace the current packaged assessment policy?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.importFile(Path(filename))
        except RoleAssessmentPolicyError as exc:
            QMessageBox.critical(self, "Unable to import role weights", str(exc))
            return
        self._defaultsRefresh()
        self._loadCurrent()

    def _export(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Role Assessment Weights",
            "roleAssessment.yaml",
            "YAML (*.yaml *.yml)",
        )
        if not filename:
            return
        try:
            self.service.exportFile(Path(filename))
        except RoleAssessmentPolicyError as exc:
            QMessageBox.critical(self, "Unable to export role weights", str(exc))