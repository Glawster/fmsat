"""Regression tests for the role browsing workspace presentation rules."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter

from fmsat.app.presentation import (
    playerNameDisplay,
    playerNameStorage,
    positionSortKey,
)
from fmsat.app.squadDetailModel import CandidateDisplay, RoleDisplay
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


def testRoleCoverageUsesEligibleCandidatesAndCompactBestFirstPresentation(qtbot) -> None:  # type: ignore[no-untyped-def]
    role = RoleDisplay(
        roleCode="deepLyingPlaymaker",
        displayName="Deep-Lying Playmaker",
        abbreviation="DLP",
        positions="DM, MC",
        phases="In Possession",
        coverage="Best: Hemp, Lauren · Backup: Maanum, Frida",
        candidates=(
            CandidateDisplay(
                name="Hemp, Lauren",
                positions="AM (L), ST (C)",
                score="88.0",
                bestRole="Wide Forward",
                breakdown="passing: 15 × 5 = 75/100",
                available=True,
            ),
            CandidateDisplay(
                name="Maanum, Frida",
                positions="M (C), AM (C)",
                score="74.0",
                bestRole="Attacking Midfielder",
                breakdown="passing: 14 × 5 = 70/100",
                available=True,
            ),
            CandidateDisplay(
                name="Stanway, Georgia",
                positions="DM, M (C)",
                score="72.0",
                bestRole="Defensive Midfielder",
                breakdown="passing: 13 × 5 = 65/100",
                available=True,
            ),
        ),
    )
    tab = SquadRolesTab((role,))
    qtbot.addWidget(tab)

    coverageItem = tab.roleTable.item(0, 1)
    coverageLabel = tab.roleTable.cellWidget(0, 1)
    assert coverageItem.text() == "Maanum, Frida, Stanway, Georgia"
    assert "Hemp" not in coverageItem.text()
    assert coverageLabel is not None
    assert "<b>Maanum, Frida</b>" in coverageLabel.text()
    assert "Best:" not in coverageLabel.text()
    assert "Backup:" not in coverageLabel.text()


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
    assert positionSortKey("STC")[0] == 0
    assert positionSortKey("AMC")[0] == 1
    assert positionSortKey("MC")[0] == 2
    assert positionSortKey("DM")[0] == 3
    assert positionSortKey("DC")[0] == 4
    assert positionSortKey("GK")[0] == 5


def testPlayerNamePresentationIsSurnameFirstWithoutChangingStoredIdentity() -> None:
    assert playerNameDisplay("Ada Player") == "Player, Ada"
    assert playerNameDisplay("N. Eizagirre") == "Eizagirre, N."
    assert playerNameStorage("Player, Ada") == "Ada Player"
    assert playerNameStorage("Eizagirre, N.") == "N. Eizagirre"
