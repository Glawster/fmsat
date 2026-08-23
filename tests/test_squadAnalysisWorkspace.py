"""Regression tests for the FMSAT Analysis workspace presentation."""

from datetime import datetime

from fmsat.app.squadAnalysisWorkspace import SquadAnalysisTab
from fmsat.app.squadDetailModel import (
    AnalysisFindingDisplay,
    PlayerRoleDisplay,
    SquadDetailModel,
)
from fmsat.core.squadModel import SquadModel


def _model() -> SquadDetailModel:
    squad = SquadModel(
        name="First Team",
        players=(),
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
        requiredPositionCount=0,
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
