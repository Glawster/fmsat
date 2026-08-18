"""Squad viewer display-model tests."""

from datetime import datetime

from fmsat.app.squadDetailModel import squadDetailModelBuild
from fmsat.core.roleDepth import RequiredSlotAssessment, SlotRoleRequirement
from fmsat.core.squadAssessment import (
    AnalysisFinding,
    GenericRoleFit,
    RequiredRoleAssessment,
    RoleCandidate,
    SquadAssessment,
)
from fmsat.core.squadModel import SquadModel, SquadModelPlayer


def testCandidateRowsExposePlayersBestAvailableRole() -> None:
    """Each candidate row should identify the player's strongest calculable role."""

    player = SquadModelPlayer("Player", "AM (C)", "", "", 0.9, ())
    squad = SquadModel(
        "First Team",
        (player,),
        datetime(2026, 8, 15),
        datetime(2026, 8, 15),
        False,
    )
    roles = (
        RequiredRoleAssessment(
            "insideForward",
            1,
            "Inside Forward",
            "IF",
            ("AML",),
            ("In Possession",),
            (RoleCandidate(player, GenericRoleFit(72.0, None, ())),),
            "Player",
            None,
            False,
        ),
        RequiredRoleAssessment(
            "shadowStriker",
            2,
            "Shadow Striker",
            "SS",
            ("AMC",),
            ("In Possession",),
            (RoleCandidate(player, GenericRoleFit(81.0, None, ())),),
            "Player",
            None,
            False,
        ),
    )
    assessment = SquadAssessment(squad, "High Press", ("High Press",), 11, roles)

    display = squadDetailModelBuild(assessment)

    assert {role.candidates[0].bestRole for role in display.roles} == {"Shadow Striker"}


def testUnresolvedSlotRoleIsVisibleAndExplicitlyUnknown() -> None:
    """Every Analysis Unknown must have an actionable semantic role in the Roles tab."""

    squad = SquadModel(
        "First Team",
        (),
        datetime(2026, 8, 18),
        datetime(2026, 8, 18),
        False,
    )
    slot = RequiredSlotAssessment(
        slotId="09",
        position="AMR",
        roles=(
            SlotRoleRequirement(
                phase="OOP",
                roleCode="trackingWinger",
                displayName="trackingWinger",
                abbreviation="trackingWinger",
            ),
        ),
        candidates=(),
        bestCandidate=None,
        backupCandidate=None,
        uncovered=True,
        unavailableReason="OOP roleCode trackingWinger has no role assessment evidence",
    )
    assessment = SquadAssessment(
        squad=squad,
        tacticName="High Press",
        availableTactics=("High Press",),
        requiredPositionCount=1,
        roles=(),
        requiredSlots=(slot,),
    )

    display = squadDetailModelBuild(assessment)

    unresolved = next(role for role in display.roles if role.roleCode == "trackingWinger")
    assert unresolved.displayName == "Tracking Winger"
    assert unresolved.resolutionState == "unknownRole"
    assert unresolved.phases == "OOP"
    assert display.requiredSlots[0].oopRole == "Unknown role"


def testUnavailableEvidenceIsNotRepeatedAsWeakPositionFinding() -> None:
    """Required Role Depth already carries unavailable evidence; findings should not duplicate it."""

    players = (
        SquadModelPlayer("Ada Player", "M (C)", "", "", 0.9, ()),
        SquadModelPlayer("Bea Example", "D (C)", "", "", 0.9, ()),
        SquadModelPlayer("Cara Sample", "D (C)", "", "", 0.9, ()),
    )
    squad = SquadModel(
        "First Team",
        players,
        datetime(2026, 8, 18),
        datetime(2026, 8, 18),
        False,
    )
    weak = AnalysisFinding(
        "trackingWinger",
        "Tracking Winger",
        "No player has complete evidence for a calculable score.",
    )
    duplication = AnalysisFinding(
        "centreBack",
        "Centre-Back",
        "3 players have this as their best role at 60.0 or above: Ada Player, Bea Example, Cara Sample.",
    )
    assessment = SquadAssessment(
        squad=squad,
        tacticName="High Press",
        availableTactics=("High Press",),
        requiredPositionCount=11,
        roles=(),
        weakRoles=(weak,),
        duplicatedRoles=(duplication,),
    )

    display = squadDetailModelBuild(assessment)

    assert all(finding.category != "Weak position" for finding in display.findings)
    assert display.findings[0].explanation == (
        "3 players have this as their best role at 60.0 or above: "
        "Player, Ada; Example, Bea; Sample, Cara."
    )
