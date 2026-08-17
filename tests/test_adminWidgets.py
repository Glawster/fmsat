"""Regression coverage for reusable administrative/editor presentation."""

from PySide6.QtWidgets import QHeaderView, QTableWidget

from fmsat.app.adminWidgets import AdminTextEditDialog, adminTableConfigure


def testAdminTextEditorAllowsLongNames(qtbot) -> None:  # type: ignore[no-untyped-def]
    dialog = AdminTextEditDialog(
        title="Rename tactic",
        label="Tactic name:",
        value="Libero Wealdstone - In Possession and Out Of Possession",
    )
    qtbot.addWidget(dialog)

    assert dialog.minimumWidth() >= 720
    assert dialog.editor.text().startswith("Libero Wealdstone")


def testAdminTableUsesAvailableFrameWithCompactIdentifierColumns(qtbot) -> None:  # type: ignore[no-untyped-def]
    table = QTableWidget(1, 4)
    qtbot.addWidget(table)

    adminTableConfigure(table, compactColumns=(1,))
    header = table.horizontalHeader()

    assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.Stretch
    assert header.sectionResizeMode(1) == QHeaderView.ResizeMode.ResizeToContents
    assert header.sectionResizeMode(2) == QHeaderView.ResizeMode.Stretch
    assert header.sectionResizeMode(3) == QHeaderView.ResizeMode.Stretch
