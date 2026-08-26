"""Regression coverage for semantic tactic-role identity in squad assessment."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

from fmsat.core.parser import TacticVocabulary
from fmsat.core.roleKnowledge import StoredRoleDefinition
from fmsat.core.squadAssessment import SquadAssessmentService
from fmsat.core.squadModel import SquadModel, SquadModelPlayer


def _service(roleKnowledge: Mock) -> SquadAssessmentService:
    return SquadAssessmentService(
        Mock(),
        Mock(),
        Mock(),
        roleKnowledge,
        TacticVocabulary(),
    )


def testCanonicalRoleResolveNormalizesLegacyAbbreviation() -> None:
    roleKnowledge = Mock()
    roleKnowledge.assessmentSettings = {}
    roleKnowledge.definitionsList.return_value = ()
    service = _service(roleKnowledge)
    position = SimpleNamespace(
        canonicalRole="HB",
        roleProfile=SimpleNamespace(description="Half-Back (Observed role)"),
    )

    assert service._canonicalRoleResolve(position) == "halfBack"


def testCanonicalRoleResolveRejectsPositionSubstitutedForRole() -> None:
    roleKnowledge = Mock()
    roleKnowledge.assessmentSettings = {}
    roleKnowledge.definitionsList.return_value = ()
    service = _service(roleKnowledge)
    position = SimpleNamespace(
        canonicalRole="AMC",
        canonicalPosition="AMC",
        identity=SimpleNamespace(value="AMC"),
        roleProfile=SimpleNamespace(description="Observed role"),
    )

    assert service._canonicalRoleResolve(position) is None


def testCanonicalRoleResolveRecoversObservedAmAfterLeakedAmcPosition() -> None:
    roleKnowledge = Mock()
    roleKnowledge.assessmentSettings = {}
    roleKnowledge.definitionsList.return_value = ()
    service = _service(roleKnowledge)
    position = SimpleNamespace(
        canonicalRole="AMC",
        canonicalPosition="AMC",
        identity=SimpleNamespace(value="AMC"),
        roleProfile=SimpleNamespace(description="AM (Observed role)"),
    )

    assert service._canonicalRoleResolve(position) == "attackingMidfielder"


def testConfirmedCustomRoleJoinsAssessmentCatalogue() -> None:
    roleKnowledge = Mock()
    roleKnowledge.assessmentSettings = {}
    roleKnowledge.weightsLoad.return_value = {"work_rate": 5}
    definition = StoredRoleDefinition(
        roleCode="trackingWinger",
        displayName="Tracking Winger",
        abbreviations=("TW",),
        positions=("AML", "AMR"),
        duties=(),
        behaviours=(),
        roleID=32,
    )
    roleKnowledge.definitionsList.return_value = (definition,)
    service = _service(roleKnowledge)
    player = SquadModelPlayer(
        name="Example Player",
        positions="AM (L)",
        ca="",
        pa="",
        confidence=1.0,
        attributes=(("work_rate", 15),),
    )
    squad = SquadModel(
        name="First Team",
        players=(player,),
        generatedAt=datetime(2026, 8, 19),
        updatedAt=datetime(2026, 8, 19),
        evidenceSuperseded=False,
        regenerationRequired=False,
    )

    catalogue = service._allRolesAssess(
        squad,
        {"trackingWinger": definition},
    )

    tracking = next(role for role in catalogue if role.roleCode == "trackingWinger")
    assert tracking.abbreviation == "TW"
    assert tracking.candidates[0].genericRoleFit.score == 75.0
