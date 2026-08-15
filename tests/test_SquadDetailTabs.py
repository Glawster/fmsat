"""Squad viewer table interaction and presentation tests."""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView

from fmsat.app.squadDetailModel import CandidateDisplay, RoleDisplay
from fmsat.app.squadDetailTabs import SquadPlayersTab, SquadRolesTab
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
            CandidateDisplay("Zulu", "ST (C)", "80.0", "weighted", True),
            CandidateDisplay("Alpha", "AM (C)", "Unavailable", "missing", False),
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
        tab.candidateTable.horizontalHeader().sectionResizeMode(3)
        is QHeaderView.ResizeMode.Stretch
    )
