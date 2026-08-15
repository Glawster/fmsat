"""Squad viewer display-model tests."""

from datetime import datetime

from fmsat.app.squadDetailModel import squadDetailModelBuild
from fmsat.core.squadAssessment import (
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
