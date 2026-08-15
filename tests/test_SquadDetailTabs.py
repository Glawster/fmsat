"""Squad viewer table interaction and presentation tests."""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QHeaderView

from fmsat.app.squadDetailModel import CandidateDisplay, RoleDisplay
from fmsat.app.squadDetailTabs import SquadPlayersTab, SquadRolesTab
from fmsat.core.config import AttributeDefinition
from fmsat.core.squadModel import SquadModel, SquadModelPlayer


def _squadModel() -> SquadModel:
    return SquadModel(
        name="First Team",
        players=(
            SquadModelPlayer(
                name="Zulu Player",
                positions="ST (C)",
                ca="",
                pa="",
                confidence=0.9,
                sourceImportSessionId=11,
                attributes=(("Finishing", 15),),
            ),
            SquadModelPlayer(
                name="Alpha Player",
                positions="D (C)",
                ca="",
                pa="",
                confidence=0.8,
                sourceImportSessionId=12,
                attributes=(("Finishing", 5),),
            ),
        ),
        generatedAt=datetime(2026, 8, 15),
        updatedAt=datetime(2026, 8, 15),
        evidenceSuperseded=False,
        regenerationRequired=False,
    )


def testPlayersTableSortRetainsPlayerProvenance(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Saving a sorted editable table must retain each player's source evidence."""

    tab = SquadPlayersTab(_squadModel())
    qtbot.addWidget(tab)
    tab.table.sortItems(0, Qt.SortOrder.AscendingOrder)

    saved = tab.modelBuild()

    assert tab.table.isSortingEnabled()
    assert [player.name for player in saved.players] == ["Alpha Player", "Zulu Player"]
    assert [player.sourceImportSessionId for player in saved.players] == [12, 11]


def testPlayersTableUsesConfiguredAttributeAbbreviationsAndWidths(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Configured attributes should all use compact, consistently sized columns."""

    attributes = (
        AttributeDefinition("Finishing", "Fin", 1),
        AttributeDefinition("Passing", "Pas", 2),
        AttributeDefinition("Vision", "Vis", 3),
    )
    tab = SquadPlayersTab(_squadModel(), attributes)
    qtbot.addWidget(tab)

    assert [tab.table.horizontalHeaderItem(column).text() for column in range(4, 7)] == [
        "Fin",
        "Pas",
        "Vis",
    ]
    assert tab.attributeNames == ("Finishing", "Passing", "Vision")
    assert {tab.table.columnWidth(column) for column in range(4, 7)} == {52}
    assert all(
        tab.table.horizontalHeader().sectionResizeMode(column)
        is QHeaderView.ResizeMode.Fixed
        for column in range(4, 7)
    )
    assert tab.table.horizontalHeaderItem(tab.table.columnCount() - 1).text() == "Known Traits"
    assert (
        tab.table.horizontalHeader().sectionResizeMode(tab.table.columnCount() - 1)
        is QHeaderView.ResizeMode.Stretch
    )
    assert all(
        tab.table.item(row, column).textAlignment() == Qt.AlignmentFlag.AlignCenter
        for row in range(tab.table.rowCount())
        for column in range(tab.table.columnCount() - 1)
    )
    assert all(
        tab.table.item(row, tab.table.columnCount() - 1).textAlignment()
        == (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        for row in range(tab.table.rowCount())
    )


def testPlayersTableFiltersRowsByPositionUnitWithoutChangingModel(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Position filters should alter presentation without removing squad players."""

    tab = SquadPlayersTab(_squadModel())
    qtbot.addWidget(tab)

    tab.positionFilters["defenders"].setChecked(False)

    defenderRow = next(
        row
        for row in range(tab.table.rowCount())
        if tab.table.item(row, 0).text() == "Alpha Player"
    )
    attackerRow = next(
        row for row in range(tab.table.rowCount()) if tab.table.item(row, 0).text() == "Zulu Player"
    )
    assert tab.table.isRowHidden(defenderRow)
    assert not tab.table.isRowHidden(attackerRow)
    assert len(tab.modelBuild().players) == 2


def testPlayersTableEditsKnownTraitsAsModelValues(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Known traits should be editable in the final player-model column."""

    tab = SquadPlayersTab(_squadModel())
    qtbot.addWidget(tab)
    traitsColumn = tab.table.columnCount() - 1
    tab.table.item(0, traitsColumn).setText("Places Shots, Curls Ball")

    saved = tab.modelBuild()

    assert saved.players[0].traits == ("Places Shots", "Curls Ball")


def testRolesTablesAreSortableAndFillAvailableWidth(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Both role selection and candidates should be sortable palette-backed tables."""

    role = RoleDisplay(
        roleCode="channelForward",
        displayName="Channel Forward",
        abbreviation="CHF",
        positions="STC",
        phases="In Possession",
        coverage="Uncovered",
        candidates=(
            CandidateDisplay("Zulu", "ST (C)", "80.0", "Channel Forward", "weighted", True),
            CandidateDisplay(
                "Alpha",
                "AM (C)",
                "Unavailable",
                "Inside Forward",
                "missing",
                False,
            ),
        ),
    )
    tab = SquadRolesTab((role,))
    qtbot.addWidget(tab)

    assert tab.roleTable.isSortingEnabled()
    assert tab.candidateTable.isSortingEnabled()
    assert (
        tab.roleTable.horizontalHeader().sectionResizeMode(2)
        is QHeaderView.ResizeMode.Stretch
    )
    assert (
        tab.candidateTable.horizontalHeader().sectionResizeMode(4)
        is QHeaderView.ResizeMode.Stretch
    )
    assert tab.candidateTable.horizontalHeaderItem(3).text() == "Best role"
    assert tab.roleTable.viewport().palette().color(QPalette.ColorRole.Base).name() == "#101f2e"
    assert (
        tab.candidateTable.viewport().palette().color(QPalette.ColorRole.Base).name()
        == "#101f2e"
    )
