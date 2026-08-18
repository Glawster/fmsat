"""Compact presentation refinements for the squad Analysis workspace."""

from __future__ import annotations

from html import escape
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidgetItem

from fmsat.app.squadDetailModel import SquadDetailModel
from fmsat.app.squadDetailTabOverrides import SquadAnalysisTab as BaseSquadAnalysisTab
from fmsat.core.config import AttributeDefinition


class SquadAnalysisTab(BaseSquadAnalysisTab):
    """Present slot depth using the same compact best-first language as Roles."""

    def __init__(
        self,
        model: SquadDetailModel,
        attributes: tuple[AttributeDefinition, ...] = (),
        requiredRows: tuple[tuple[str, str], ...] = (),
        parent=None,
    ) -> None:
        super().__init__(model, attributes, requiredRows, parent)
        self._depthCoverageCompact()

    def _depthCoverageCompact(self) -> None:
        """Remove repetitive Best/Backup prose while retaining full evidence as a tooltip."""

        for row in range(self.depthTable.rowCount()):
            item = self.depthTable.item(row, 1)
            if item is None:
                continue
            original = item.text()
            text, html = coverageCompactRender(original)
            item.setText(text)
            item.setToolTip(original)

            label = QLabel(html, self.depthTable)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            label.setStyleSheet("background: transparent;")
            label.setToolTip(original)
            self.depthTable.setCellWidget(row, 1, label)


def coverageCompactRender(value: str) -> tuple[str, str]:
    """Return plain and rich compact coverage while preserving phase prefixes."""

    parts = value.split(" | ")
    rendered = [_coveragePartCompact(part) for part in parts]
    return (
        " | ".join(text for text, _html in rendered),
        " | ".join(html for _text, html in rendered),
    )


def _coveragePartCompact(value: str) -> tuple[str, str]:
    """Compact one direct or phase-prefixed Best/Backup coverage statement."""

    match = re.match(
        r"^(?P<prefix>.*?)(?:Best:\s*)(?P<best>.+?)(?:\s*·\s*(?P<rest>.*))?$",
        value,
    )
    if match is None:
        return value, escape(value)

    prefix = match.group("prefix") or ""
    best = match.group("best").strip()
    rest = (match.group("rest") or "").strip()
    backupMatch = re.match(r"Backup:\s*(.+)$", rest)
    backup = backupMatch.group(1).strip() if backupMatch is not None else ""

    names = best if not backup else f"{best}, {backup}"
    htmlNames = f"<b>{escape(best)}</b>"
    if backup:
        htmlNames += f", {escape(backup)}"
    return f"{prefix}{names}", f"{escape(prefix)}{htmlNames}"
