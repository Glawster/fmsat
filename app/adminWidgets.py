"""Shared presentation helpers for FMSAT administrative/editor screens."""

from __future__ import annotations

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

adminStyle = """
QDialog#adminEditDialog, QDialog#adminTextEditDialog {
    background: #ffffff;
    color: #202020;
}
QDialog#adminEditDialog QLabel, QDialog#adminTextEditDialog QLabel {
    color: #202020;
    background: transparent;
}
QDialog#adminEditDialog QTabWidget::pane {
    background: #ffffff;
    border: 1px solid #b8b8b8;
}
QDialog#adminEditDialog QTabBar::tab {
    background: #eeeeee;
    color: #202020;
    border: 1px solid #b8b8b8;
    padding: 5px 10px;
}
QDialog#adminEditDialog QTabBar::tab:selected {
    background: #ffffff;
}
QDialog#adminEditDialog QTableWidget {
    background: #ffffff;
    alternate-background-color: #f7f7f7;
    color: #202020;
    gridline-color: #cccccc;
    selection-background-color: #d9e9ff;
    selection-color: #202020;
}
QDialog#adminEditDialog QTableWidget QWidget#qt_scrollarea_viewport {
    background: #ffffff;
}
QDialog#adminEditDialog QHeaderView::section {
    background: #f0f0f0;
    color: #202020;
    border: 0;
    border-right: 1px solid #c8c8c8;
    border-bottom: 1px solid #c8c8c8;
    padding: 5px;
}
QDialog#adminEditDialog QTableCornerButton::section {
    background: #f0f0f0;
    border: 0;
    border-right: 1px solid #c8c8c8;
    border-bottom: 1px solid #c8c8c8;
}
QDialog#adminTextEditDialog QLineEdit {
    background: #ffffff;
    color: #202020;
    border: 1px solid #a9a9a9;
    border-radius: 2px;
    padding: 6px;
}
QDialog#adminEditDialog QPushButton, QDialog#adminTextEditDialog QPushButton {
    background: #eeeeee;
    color: #202020;
    border: 1px solid #a9a9a9;
    border-radius: 2px;
    padding: 6px 12px;
}
QDialog#adminEditDialog QPushButton:hover, QDialog#adminTextEditDialog QPushButton:hover {
    background: #e2e2e2;
}
"""


class AdminEditDialog(QDialog):
    """Provide the standard light frame used by model/data editing dialogs."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("adminEditDialog")
        self.setStyleSheet(adminStyle)
        self.setMinimumSize(900, 600)
        self.resize(1200, 760)


class AdminTextEditDialog(QDialog):
    """Standard light admin frame for editing one long text value."""

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
        self.setStyleSheet(adminStyle)
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
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
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
