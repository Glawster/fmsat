"""Shared presentation helpers for FMSAT administrative/editor screens."""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)


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


class AdminTextEditDialog(QDialog):
    """Standard compact admin frame for editing one long text value."""

    def __init__(
        self,
        *,
        title: str,
        label: str,
        value: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("adminTextEditDialog")
        self.setStyleSheet(
            files("fmsat.app").joinpath("fmsat.qss").read_text(encoding="utf-8")
        )
        self.setWindowTitle(title)
        self.setMinimumWidth(720)
        self.resize(760, 150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        prompt = QLabel(label, self)
        prompt.setObjectName("adminFieldLabel")
        layout.addWidget(prompt)

        self.editor = QLineEdit(value, self)
        self.editor.setObjectName("adminTextEditor")
        self.editor.selectAll()
        layout.addWidget(self.editor)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self) -> str:
        """Return the edited value without surrounding whitespace."""

        return self.editor.text().strip()


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
