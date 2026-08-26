"""Regression tests for the role browsing workspace presentation rules."""

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QWidget

from fmsat.app.presentation import (
    playerNameDisplay,
    playerNameStorage,
    positionSortKey,
    roleAbbreviationDisplay,
)
from fmsat.app.squadDetailModel import CandidateDisplay, RoleDisplay
from fmsat.app.squadRolesWorkspace import SquadRolesTab
from fmsat.core.config import AttributeDefinition


def _role(
    code: str,
    abbreviation: str,
    positions: str,
    playerName: str = "Player, Ada",
    phases: str = "In Possession",
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
        phases=phases,
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

    assert tab.roleTable.columnCount() == 3
    assert [tab.roleTable.horizontalHeaderItem(column).text() for column in range(3)] == [
        "IP",
        "OOP",
        "Coverage",
    ]
    mainSplitter = tab.findChild(QSplitter, "roleWorkspaceSplitter")
    evidenceSplitter = tab.findChild(QSplitter, "roleEvidenceSplitter")
    assert mainSplitter is not None
    assert evidenceSplitter is not None
    assert mainSplitter.orientation() is Qt.Orientation.Horizontal
    assert evidenceSplitter.orientation() is Qt.Orientation.Vertical


def testTacticRolesSeparatePossessionPhaseAndUseSurnameOnlyCoverage(qtbot) -> None:  # type: ignore[no-untyped-def]
    candidates = (
        CandidateDisplay(
            name="Russo, Alessia",
            positions="ST (C)",
            score="80.0",
            bestRole="Centre Forward",
            breakdown="finishing: 16 × 5 = 80/100",
            available=True,
        ),
        CandidateDisplay(
            name="Freigang, Laura",
            positions="ST (C)",
            score="75.0",
            bestRole="Centre Forward",
            breakdown="finishing: 15 × 5 = 75/100",
            available=True,
        ),
    )
    roles = (
        RoleDisplay(
            roleCode="centreForward",
            displayName="Centre Forward",
            abbreviation="CF",
            positions="STC",
            phases="In Possession",
            coverage="",
            candidates=candidates,
        ),
        RoleDisplay(
            roleCode="trackingCentreForward",
            displayName="Tracking Centre Forward",
            abbreviation="TCF",
            positions="STC",
            phases="Out Of Possession",
            coverage="",
            candidates=candidates,
        ),
    )
    tab = SquadRolesTab(roles)
    qtbot.addWidget(tab)

    assert [tab.roleTable.item(0, column).text() for column in range(3)] == [
        "CF",
        "",
        "Russo - Freigang",
    ]
    assert [tab.roleTable.item(1, column).text() for column in range(3)] == [
        "",
        "TCF",
        "Russo - Freigang",
    ]


def testFirstRoleSelectionSortsCandidatesByGenericRoleFitDescending(qtbot) -> None:  # type: ignore[no-untyped-def]
    candidates = (
        CandidateDisplay(
            name="Lower, Player",
            positions="ST (C)",
            score="61.0",
            bestRole="Centre Forward",
            breakdown="finishing: 12 × 5 = 60/100",
            available=True,
        ),
        CandidateDisplay(
            name="Higher, Player",
            positions="ST (C)",
            score="84.0",
            bestRole="Centre Forward",
            breakdown="finishing: 17 × 5 = 85/100",
            available=True,
        ),
    )
    role = RoleDisplay(
        roleCode="centreForward",
        displayName="Centre Forward",
        abbreviation="CF",
        positions="STC",
        phases="In Possession",
        coverage="",
        candidates=candidates,
    )
    tab = SquadRolesTab((role,))
    qtbot.addWidget(tab)

    tab.roleTable.setCurrentCell(0, 0)

    assert [tab.candidateTable.item(row, 2).text() for row in range(2)] == ["84.0", "61.0"]
    assert (
        tab.candidateTable.horizontalHeader().sortIndicatorOrder() is Qt.SortOrder.DescendingOrder
    )


def testRoleCoverageUsesEligibleCandidatesAndNativeTableFont(qtbot) -> None:  # type: ignore[no-untyped-def]
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

    coverageItem = tab.roleTable.item(0, 2)
    assert coverageItem.text() == "Maanum - Stanway"
    assert "Hemp" not in coverageItem.text()
    assert tab.roleTable.cellWidget(0, 2) is None


def testPlayerRoleAssessmentUsesUnionOfRequiredAttributes(qtbot) -> None:  # type: ignore[no-untyped-def]
    playerName = "Freigang, Laura"
    roles = (
        RoleDisplay(
            roleCode="secondStriker",
            displayName="Second Striker",
            abbreviation="SS",
            positions="AMC, STC",
            phases="In Possession",
            coverage="",
            candidates=(
                CandidateDisplay(
                    name=playerName,
                    positions="AM (C), ST (C)",
                    score="81.0",
                    bestRole="Second Striker",
                    breakdown="finishing: 16 × 8 = 128/160; off_the_ball: 15 × 7 = 105/140",
                    available=True,
                ),
            ),
        ),
        RoleDisplay(
            roleCode="centreForward",
            displayName="Centre Forward",
            abbreviation="CF",
            positions="STC",
            phases="In Possession",
            coverage="",
            candidates=(
                CandidateDisplay(
                    name=playerName,
                    positions="AM (C), ST (C)",
                    score="77.0",
                    bestRole="Second Striker",
                    breakdown="finishing: 16 × 7 = 112/140; strength: 11 × 5 = 55/100",
                    available=True,
                ),
            ),
        ),
    )
    attributes = (
        AttributeDefinition("finishing", "Fin", 1),
        AttributeDefinition("off_the_ball", "OtB", 2),
        AttributeDefinition("strength", "Str", 3),
    )
    tab = SquadRolesTab(roles, attributes)
    qtbot.addWidget(tab)

    tab._playerRolesShow(playerName)

    assert [
        tab.playerRoleTable.horizontalHeaderItem(column).text()
        for column in range(tab.playerRoleTable.columnCount())
    ] == ["Role", "Name", "Generic Role Fit", "Fin", "OtB", "Str"]
    assert [tab.playerRoleTable.item(0, column).text() for column in range(3, 6)] == [
        "16",
        "15",
        "—",
    ]
    assert [tab.playerRoleTable.item(1, column).text() for column in range(3, 6)] == [
        "16",
        "—",
        "11",
    ]
    assert tab.playerRoleTable.horizontalHeaderItem(4).toolTip() == "off_the_ball"


def testRoleOrderStaysTacticalUntilPhaseHeaderIsClicked(qtbot) -> None:  # type: ignore[no-untyped-def]
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


def testAllPlayerViewOmitsCalculationBreakdown(qtbot) -> None:  # type: ignore[no-untyped-def]
    roles = (
        _role("insideForward", "IF", "AML", "Hemp, Lauren", "In Possession"),
        _role("trackingWinger", "TW", "AML", "Hemp, Lauren", "Out Of Possession"),
    )
    tab = SquadRolesTab(roles)
    qtbot.addWidget(tab)

    assert [
        tab.candidateTable.horizontalHeaderItem(column).text()
        for column in range(tab.candidateTable.columnCount())
    ] == ["Player", "Natural positions", "Generic Role Fit", "Best role"]
    assert tab.candidateTable.rowCount() == 1
    assert tab.candidateTable.item(0, 0).text() == "Hemp, Lauren"


def testUnresolvedSemanticRoleCodeDisplaysUnknownAbbreviation() -> None:
    assert roleAbbreviationDisplay("trackingWinger", "trackingWinger") == "Unknown"
    assert roleAbbreviationDisplay("trackingWideMidfielder", "trackingWideMidfielder") == "Unknown"
    assert roleAbbreviationDisplay("trackingCentreForward", "TCF") == "TCF"


def testUnknownRolePointsToExistingRoleEditorWorkflow(qtbot) -> None:  # type: ignore[no-untyped-def]
    class Host(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.tacticVocabulary = SimpleNamespace(roles={})
            self.roleImportCount = 0

        def roleProfileImport(self) -> None:
            self.roleImportCount += 1

    host = Host()
    qtbot.addWidget(host)
    role = _role("trackingWinger", "Unknown", "AMR")
    tab = SquadRolesTab((role,), parent=host)

    item = tab.roleTable.item(0, 0)
    assert item.text() == "Unknown"
    assert "Role Editor" in item.toolTip()

    tab._unknownRoleEdit(0, 0)

    assert host.roleImportCount == 1


def testPlayerNamePresentationIsSurnameFirstWithoutChangingStoredIdentity() -> None:
    assert playerNameDisplay("Ada Player") == "Player, Ada"
    assert playerNameDisplay("N. Eizagirre") == "Eizagirre, N."
    assert playerNameStorage("Player, Ada") == "Ada Player"
    assert playerNameStorage("Eizagirre, N.") == "N. Eizagirre"
