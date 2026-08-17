"""Shared presentation helpers for FMSAT administrative/editor screens."""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtWidgets import QDialog, QHeaderView, QTableWidget, QWidget


class AdminEditDialog(QDialog):
    """Provide the standard frame used by model/data editing dialogs."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("adminEditDialog")
        self.setStyleSheet(
            files("fmsat.app").joinpath("fmsat.qss").read_text(encoding="utf-8")
        )
        self.setMinimumSize(900, 600)
        self.resize(1200, 760)


def adminTableConfigure(
    table: QTableWidget,
    *,
    compactColumns: tuple[int, ...] = (),
) -> None:
    """Make an editor table fill its frame while keeping terse fields compact."""

    table.setAlternatingRowColors(True)
    table.setWordWrap(False)
    table.verticalHeader().setVisible(True)
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    for column in range(table.columnCount()):
        mode = (
            QHeaderView.ResizeMode.ResizeToContents
            if column in compactColumns
            else QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(column, mode)
