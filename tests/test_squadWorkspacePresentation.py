"""Regression coverage for squad workspace presentation wiring."""

from datetime import datetime

from fmsat.app.squadAnalysisWorkspace import SquadAnalysisTab
from fmsat.app.squadDetailModel import RequiredSlotDisplay, SquadDetailModel
from fmsat.app.squadPlayersWorkspace import SquadPlayersTab
from fmsat.core.squadModel import SquadModel, SquadModelPlayer


def _squad() -> SquadModel:
    return SquadModel(
        name="First Team",
        players=(
            SquadModelPlayer(
                name="Georgia Stanway",
                positions="DM, M (C)",
                ca="",
                pa="",
                confidence=1.0,
                attributes=(),
            ),
        ),
        generatedAt=datetime(2026, 8, 18),
        updatedAt=datetime(2026, 8, 18),
        evidenceSuperseded=False,
    )


def testPlayersTabShowsSurnameFirstButSavesStoredIdentity(qtbot) -> None:  # type: ignore[no-untyped-def]
    tab = SquadPlayersTab(_squad())
    qtbot.addWidget(tab)

    assert tab.table.item(0, 0).text() == "Stanway, Georgia"
    assert tab.modelBuild().players[0].name == "Georgia Stanway"


def testAnalysisUsesFourColumnSlotDepthFromFmsatIntelligence(qtbot) -> None:  # type: ignore[no-untyped-def]
    model = SquadDetailModel(
        squad=_squad(),
        tacticName="Libero1974",
        availableTactics=("Libero1974",),
        sourceStatus="Generated from screenshot evidence",
        updated="18 Aug 2026 13:00",
        requiredPositionCount=1,
        roles=(),
        requiredSlots=(
            RequiredSlotDisplay(
                position="DM",
                ipRole="HB",
                oopRole="PDM",
                primary="Stanway, Georgia · 84.0 / 78.0",
                backup="Walsh, Keira · 80.0 / 76.0",
                primaryEvidence="IP Half Back: 84.0; OOP Pressing Defensive Midfielder: 78.0; Combined slot score: 81.0",
                backupEvidence="IP Half Back: 80.0; OOP Pressing Defensive Midfielder: 76.0; Combined slot score: 78.0",
            ),
        ),
    )
    tab = SquadAnalysisTab(model)
    qtbot.addWidget(tab)

    assert [
        tab.depthTable.horizontalHeaderItem(column).text()
        for column in range(tab.depthTable.columnCount())
    ] == ["IP Role", "OOP Role", "Primary", "Backup"]
    assert tab.depthTable.item(0, 0).text() == "HB"
    assert tab.depthTable.item(0, 1).text() == "PDM"
    assert tab.depthTable.item(0, 2).text() == "Stanway, Georgia · 84.0 / 78.0"
    assert "OOP Pressing Defensive Midfielder" in tab.depthTable.item(0, 2).toolTip()
