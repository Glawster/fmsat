"""UI regression proving the Analysis Best XI uses the global assignment service."""

from datetime import datetime

from fmsat.app.squadAnalysisWorkspace import SquadAnalysisTab
from fmsat.app.squadDetailModel import (
    CandidateDisplay,
    RequiredSlotDisplay,
    RoleDisplay,
    SquadDetailModel,
)
from fmsat.core.squadModel import SquadModel, SquadModelPlayer


def _candidate(name: str, positions: str, score: float) -> CandidateDisplay:
    return CandidateDisplay(
        name=name,
        positions=positions,
        score=f"{score:.1f}",
        bestRole="",
        breakdown="",
        available=True,
    )


def _role(code: str, abbreviation: str, phase: str, candidates) -> RoleDisplay:
    return RoleDisplay(
        roleCode=code,
        displayName=code,
        abbreviation=abbreviation,
        positions="",
        phases=phase,
        coverage="",
        candidates=tuple(candidates),
    )


def _slot(position: str, ipRole: str, oopRole: str, legacyPrimary: str) -> RequiredSlotDisplay:
    roleCodes = {
        "SS": "secondStriker",
        "TAM": "trackingAttackingMidfielder",
        "IF": "insideForward",
        "TW": "trackingWinger",
    }
    return RequiredSlotDisplay(
        position=position,
        ipRole=ipRole,
        oopRole=oopRole,
        primary=legacyPrimary,
        backup="—",
        primaryEvidence="legacy role-depth primary",
        backupEvidence="",
        ipRoleCode=roleCodes[ipRole],
        oopRoleCode=roleCodes[oopRole],
    )


def testAnalysisBestXiCanMoveLocalBestToCoverAnotherSlot(qtbot) -> None:  # type: ignore[no-untyped-def]
    squad = SquadModel(
        name="Test Squad",
        players=(
            SquadModelPlayer(
                name="Lauren Hemp",
                positions="AM (L), ST (C)",
                ca="",
                pa="",
                confidence=1.0,
                attributes=(),
            ),
            SquadModelPlayer(
                name="Laura Freigang",
                positions="AM (C), ST (C)",
                ca="",
                pa="",
                confidence=1.0,
                attributes=(),
            ),
        ),
        generatedAt=datetime(2026, 8, 22),
        updatedAt=datetime(2026, 8, 22),
        evidenceSuperseded=False,
    )
    hempSs = _candidate("Hemp, Lauren", "AM (L), ST (C)", 81.0)
    freigangSs = _candidate("Freigang, Laura", "AM (C), ST (C)", 77.0)
    hempWide = _candidate("Hemp, Lauren", "AM (L), ST (C)", 75.0)
    roles = (
        _role("secondStriker", "SS", "In Possession", (hempSs, freigangSs)),
        _role("trackingAttackingMidfielder", "TAM", "Out Of Possession", (hempSs, freigangSs)),
        _role("insideForward", "IF", "In Possession", (hempWide,)),
        _role("trackingWinger", "TW", "Out Of Possession", (hempWide,)),
    )
    model = SquadDetailModel(
        squad=squad,
        tacticName="Test Tactic",
        availableTactics=("Test Tactic",),
        sourceStatus="Generated from screenshot evidence",
        updated="22 Aug 2026 13:00",
        requiredPositionCount=2,
        roles=roles,
        requiredSlots=(
            _slot("AMC", "SS", "TAM", "Hemp, Lauren"),
            _slot("AML", "IF", "TW", "Uncovered"),
        ),
    )

    tab = SquadAnalysisTab(model)
    qtbot.addWidget(tab)

    assert tab.bestXiTable.item(0, 3).text() == "Freigang, Laura"
    assert tab.bestXiTable.item(1, 3).text() == "Hemp, Lauren"
    assert "stronger global XI" in tab.bestXiTable.item(0, 3).toolTip()
