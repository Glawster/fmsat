"""Regression tests for the FMSAT Analysis workspace presentation."""

from datetime import datetime
from types import SimpleNamespace

from fmsat.app.squadAnalysisWorkspace import SquadAnalysisTab
from fmsat.app.squadDetailModel import (
    AnalysisFindingDisplay,
    PlayerRoleDisplay,
    RequiredSlotDisplay,
    SquadDetailModel,
)
from fmsat.core.squadModel import SquadModel, SquadModelPlayer


def _model() -> SquadDetailModel:
    squad = SquadModel(
        name="First Team",
        players=(
            SquadModelPlayer(
                name="Georgia Stanway",
                positions="M (C)",
                ca="",
                pa="",
                confidence=None,
                attributes=(),
            ),
        ),
        generatedAt=datetime(2026, 8, 18),
        updatedAt=datetime(2026, 8, 18),
        evidenceSuperseded=False,
        regenerationRequired=False,
    )
    return SquadDetailModel(
        squad=squad,
        tacticName="Test Tactic",
        availableTactics=("Test Tactic",),
        sourceStatus="Generated from screenshot evidence",
        updated="18 Aug 2026 13:00",
        requiredPositionCount=1,
        roles=(),
        playerRoles=(
            PlayerRoleDisplay(
                name="Stanway, Georgia",
                bestRole="Box-to-Box Midfielder",
                bestScore="84.0",
                bestBreakdown="decisions: 16 × 3 = 48/60",
                alternatives="Defensive Midfielder, Centre-Back",
            ),
        ),
        findings=(
            AnalysisFindingDisplay(
                category="Role duplication",
                subject="Centre-Back",
                explanation=(
                    "4 players have this as their best role at 60.0 or above: "
                    "Lawley, Gemma, Wos, Oliwia, Agrez, Sara, Struck, Sille."
                ),
            ),
        ),
        requiredSlots=(
            RequiredSlotDisplay(
                position="MC",
                ipRole="BBM",
                oopRole="CM",
                primary="Stanway, Georgia · 86.0 / 82.0",
                backup="Wos, Oliwia · 78.0 / 76.0",
                primaryEvidence="IP BBM 86.0; OOP CM 82.0; slot fit 84.0",
                backupEvidence="IP BBM 78.0; OOP CM 76.0; slot fit 77.0",
            ),
        ),
    )


def testPlayerRoleStrengthsOmitsScoreBreakdown(qtbot) -> None:  # type: ignore[no-untyped-def]
    tab = SquadAnalysisTab(_model())
    qtbot.addWidget(tab)

    assert tab.playerTable.columnCount() == 4
    assert [
        tab.playerTable.horizontalHeaderItem(column).text()
        for column in range(tab.playerTable.columnCount())
    ] == ["Player", "Best role", "Generic Role Fit", "Alternative roles"]


def testFindingPlayerListsUseSemicolonSeparators(qtbot) -> None:  # type: ignore[no-untyped-def]
    tab = SquadAnalysisTab(_model())
    qtbot.addWidget(tab)

    evidence = tab.findingsTable.item(0, 2).text()
    assert "Lawley, Gemma; Wos, Oliwia; Agrez, Sara; Struck, Sille." in evidence


def testAnalysisUsesFourBalancedDashboardCards(qtbot) -> None:  # type: ignore[no-untyped-def]
    tab = SquadAnalysisTab(_model())
    qtbot.addWidget(tab)

    root = tab.layout()
    assert root is not None
    dashboard = root.itemAt(root.count() - 1).layout()
    assert dashboard is not None
    assert dashboard.count() == 4


def testBestXiUsesSharedFmsatAnalysisTableStyle(qtbot) -> None:  # type: ignore[no-untyped-def]
    tab = SquadAnalysisTab(_model())
    qtbot.addWidget(tab)

    assert tab.bestXiTable.objectName() == "roleDepthAnalysisTable"
    assert tab.bestXiTable.alternatingRowColors()


def testBestXiUsesUniquePrimarySlotAssignment(qtbot) -> None:  # type: ignore[no-untyped-def]
    tab = SquadAnalysisTab(_model())
    qtbot.addWidget(tab)

    assert tab.bestXiTable.rowCount() == 1
    assert [
        tab.bestXiTable.horizontalHeaderItem(column).text()
        for column in range(tab.bestXiTable.columnCount())
    ] == ["Position", "IP Role", "OOP Role", "Selected Player", "Position Status"]
    assert tab.bestXiTable.item(0, 0).text() == "MC"
    assert tab.bestXiTable.item(0, 1).text() == "BBM"
    assert tab.bestXiTable.item(0, 2).text() == "CM"
    assert tab.bestXiTable.item(0, 3).text() == "Stanway, Georgia"
    assert "slot fit 84.0" in tab.bestXiTable.item(0, 3).toolTip()
    assert tab.bestXiTable.item(0, 4).text() == "Familiar"


def testBestXiPreservesUnavailablePrimaryState(qtbot) -> None:  # type: ignore[no-untyped-def]
    model = _model()
    unavailableSlot = RequiredSlotDisplay(
        position="STC",
        ipRole="CF",
        oopRole="TCF",
        primary="Unavailable",
        backup="Unavailable",
        primaryEvidence="Required slot aggregation policy is unavailable",
        backupEvidence="Required slot aggregation policy is unavailable",
    )
    unavailableModel = SquadDetailModel(
        squad=model.squad,
        tacticName=model.tacticName,
        availableTactics=model.availableTactics,
        sourceStatus=model.sourceStatus,
        updated=model.updated,
        requiredPositionCount=1,
        roles=model.roles,
        scoringIdentity=model.scoringIdentity,
        playerRoles=model.playerRoles,
        findings=model.findings,
        requiredSlots=(unavailableSlot,),
    )

    tab = SquadAnalysisTab(unavailableModel)
    qtbot.addWidget(tab)

    assert tab.bestXiTable.item(0, 3).text() == "Unavailable"
    assert tab.bestXiTable.item(0, 4).text() == "—"
    assert "aggregation policy" in tab.bestXiTable.item(0, 3).toolTip()


def testBestXiUncoveredSlotDoesNotClaimFamiliarityUnavailable(qtbot) -> None:  # type: ignore[no-untyped-def]
    model = _model()
    uncoveredSlot = RequiredSlotDisplay(
        position="AML",
        ipRole="IF",
        oopRole="TW",
        primary="Uncovered",
        backup="—",
        primaryEvidence="No player has complete calculable evidence for every phase role.",
        backupEvidence="No player has complete calculable evidence for every phase role.",
    )
    uncoveredModel = SquadDetailModel(
        squad=model.squad,
        tacticName=model.tacticName,
        availableTactics=model.availableTactics,
        sourceStatus=model.sourceStatus,
        updated=model.updated,
        requiredPositionCount=1,
        roles=model.roles,
        scoringIdentity=model.scoringIdentity,
        playerRoles=model.playerRoles,
        findings=model.findings,
        requiredSlots=(uncoveredSlot,),
    )

    tab = SquadAnalysisTab(uncoveredModel)
    qtbot.addWidget(tab)

    assert tab.bestXiTable.item(0, 3).text() == "Uncovered"
    assert tab.bestXiTable.item(0, 4).text() == "Uncovered"


def testBestXiPositionStatusUsesCapturedSquadPositions() -> None:
    player = SimpleNamespace(positions="DM, M (C)")

    status, evidence = SquadAnalysisTab._positionStatus("MC", player)

    assert status == "Familiar"
    assert "M (C)" in evidence


def testBestXiPositionStatusFlagsTrainingWhenPositionWasNotCaptured() -> None:
    player = SimpleNamespace(positions="DM, M (C)")

    status, evidence = SquadAnalysisTab._positionStatus("STC", player)

    assert status == "Training required"
    assert "Positional training would be required" in evidence
    assert "DM, M (C)" in evidence


def testBestXiPositionStatusDoesNotGuessWhenPositionsAreMissing() -> None:
    player = SimpleNamespace(positions="")

    status, evidence = SquadAnalysisTab._positionStatus("STC", player)

    assert status == "Familiarity unavailable"
    assert "No player positions were captured" in evidence
