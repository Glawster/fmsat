"""Regression tests for the role browsing workspace presentation rules."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter

from fmsat.app.presentation import playerNameDisplay, playerNameStorage
from fmsat.app.squadDetailModel import CandidateDisplay, RoleDisplay, _positionSortKey
from fmsat.app.squadRolesWorkspace import SquadRolesTab


def _role(
    code: str,
    abbreviation: str,
    positions: str,
    playerName: str = "Player, Ada",
) -> RoleDisplay:
    candidate = CandidateDisplay(
        name=playerName,
        positions=positions,
        score="70.0",
        bestRole=code,
        breakdown="decisions: 14 × 5 = 70/100",
        available=True,
    )
    return RoleDisplay(
        roleCode=code,
        displayName=code,
        abbreviation=abbreviation,
        positions=positions,
        phases="In Possession",
        coverage=f"Best: {playerName} · no calculated backup",
        candidates=(candidate,),
    )


def testRolesWorkspaceUsesFullHeightRolePaneAndStackedEvidence(qtbot) -> None:  # type: ignore[no-untyped-def]
    roles = (
        _role("Channel Forward", "CHF", "STC"),
        _role("Attacking Midfielder", "AM", "AMC"),
        _role("Deep-Lying Playmaker", "DLP", "MC"),
        _role("Defensive Midfielder", "DM", "DM"),
        _role("Centre-Back", "CB", "DC"),
        _role("Sweeper Keeper", "SK", "GK"),
    )
    tab = SquadRolesTab(roles)
    qtbot.addWidget(tab)

    assert tab.roleTable.columnCount() == 2
    assert [tab.roleTable.horizontalHeaderItem(column).text() for column in range(2)] == [
        "Role",
        "Coverage",
    ]
    mainSplitter = tab.findChild(QSplitter, "roleWorkspaceSplitter")
    evidenceSplitter = tab.findChild(QSplitter, "roleEvidenceSplitter")
    assert mainSplitter is not None
    assert evidenceSplitter is not None
    assert mainSplitter.orientation() is Qt.Orientation.Horizontal
    assert evidenceSplitter.orientation() is Qt.Orientation.Vertical


def testRoleOrderStaysTacticalUntilRoleHeaderIsClicked(qtbot) -> None:  # type: ignore[no-untyped-def]
    roles = (
        _role("Channel Forward", "CHF", "STC"),
        _role("Attacking Midfielder", "AM", "AMC"),
        _role("Deep-Lying Playmaker", "DLP", "MC"),
        _role("Defensive Midfielder", "DM", "DM"),
        _role("Centre-Back", "CB", "DC"),
        _role("Sweeper Keeper", "SK", "GK"),
    )
    tab = SquadRolesTab(roles)
    qtbot.addWidget(tab)

    assert [tab.roleTable.item(row, 0).text() for row in range(tab.roleTable.rowCount())] == [
        "CHF",
        "AM",
        "DLP",
        "DM",
        "CB",
        "SK",
    ]

    tab._roleHeaderClicked(0)

    assert [tab.roleTable.item(row, 0).text() for row in range(tab.roleTable.rowCount())] == [
        "AM",
        "CB",
        "CHF",
        "DLP",
        "DM",
        "SK",
    ]


def testSquadRoleLineOrderingRunsFromForwardsToGoalkeeper() -> None:
    assert _positionSortKey("STC")[0] == 0
    assert _positionSortKey("AMC")[0] == 1
    assert _positionSortKey("MC")[0] == 2
    assert _positionSortKey("DM")[0] == 3
    assert _positionSortKey("DC")[0] == 4
    assert _positionSortKey("GK")[0] == 5


def testPlayerNamePresentationIsSurnameFirstWithoutChangingStoredIdentity() -> None:
    assert playerNameDisplay("Ada Player") == "Player, Ada"
    assert playerNameDisplay("N. Eizagirre") == "Eizagirre, N."
    assert playerNameStorage("Player, Ada") == "Ada Player"
    assert playerNameStorage("Eizagirre, N.") == "N. Eizagirre"
