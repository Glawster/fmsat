"""Tests for explainable, role-level squad assessment."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

from fmsat.core.squadAssessment import (
    GenericRoleFit,
    GenericRoleFitCalculator,
    RequiredRoleAssessment,
    RoleCandidate,
    SquadAssessmentService,
)
from fmsat.core.config import Configuration
from fmsat.core.parser import TacticVocabulary
from fmsat.core.roleKnowledge import StoredRoleDefinition
from fmsat.core.squadModel import SquadModel, SquadModelPlayer


def _player(attributes: tuple[tuple[str, int | None], ...]) -> SquadModelPlayer:
    return SquadModelPlayer(
        name="Example Player",
        positions="D/WB (L)",
        ca="",
        pa="",
        confidence=0.9,
        attributes=attributes,
    )


def testGenericRoleFitUsesExplicitWeightsAndExplainsCalculation() -> None:
    """Each weighted attribute should remain visible in the result."""

    result = GenericRoleFitCalculator().calculate(
        _player((("Crossing", 15), ("Work Rate", 10))),
        {"Crossing": 5, "Work Rate": 2, "Finishing": 0},
    )

    assert result.score == 67.9
    assert tuple(item.attribute for item in result.contributions) == (
        "Crossing",
        "Work Rate",
    )
    assert result.contributions[0].weightedPoints == 75
    assert result.contributions[0].maximumPoints == 100


def testGenericRoleFitIsUnavailableWhenRequiredDataIsMissing() -> None:
    """Missing model facts must not be represented by a zero score."""

    result = GenericRoleFitCalculator().calculate(
        _player((("Crossing", 15),)),
        {"Crossing": 5, "Work Rate": 2},
    )

    assert result.score is None
    assert result.unavailableReason == "Missing attributes: Work Rate"


def testGenericRoleFitIsUnavailableWithoutRoleWeights() -> None:
    """An undefined role assessment must remain explicitly unavailable."""

    result = GenericRoleFitCalculator().calculate(_player(()), {})

    assert result.score is None
    assert result.unavailableReason == "No assessment weights are defined"


def testPackagedWeightsCoverEveryAssessableTacticRole() -> None:
    """Configured role policies must be explicit and valid for known assessable roles."""

    configuration = Configuration()
    weights = configuration.roleAssessmentWeights()
    vocabulary = TacticVocabulary()

    assert set(weights).issubset(set(vocabulary.roles))
    assert vocabulary.roleNormalize("TAM").value == "trackingAttackingMidfielder"
    assert weights["trackingAttackingMidfielder"]
    assert all(roleWeights for roleWeights in weights.values())
    assert all(
        1 <= weight <= 10
        for roleWeights in weights.values()
        for weight in roleWeights.values()
    )


def testSquadAssessmentUsesUniqueRoleRatherThanPositionOrSlot() -> None:
    """A repeated canonical role should produce one role-level assessment."""

    player = _player((("Crossing", 15),))
    squad = SquadModel(
        name="Test Squad",
        players=(player,),
        generatedAt=datetime(2026, 8, 14),
        updatedAt=datetime(2026, 8, 14),
        evidenceSuperseded=False,
        regenerationRequired=False,
    )
    positions = [
        SimpleNamespace(
            canonicalRole="advancedWingBack",
            canonicalPosition="WBL",
            identity=SimpleNamespace(value="WBL"),
        ),
        SimpleNamespace(
            canonicalRole="advancedWingBack",
            canonicalPosition="WBR",
            identity=SimpleNamespace(value="WBR"),
        ),
    ]
    database = Mock()
    database.squadAppliedTactics.return_value = ("High Press",)
    squadModels = Mock()
    squadModels.modelLoad.return_value = squad
    tacticModels = Mock()
    tacticModels.tacticLoad.return_value = SimpleNamespace(
        tactic=SimpleNamespace(
            inPossession=SimpleNamespace(positions=positions),
            outOfPossession=SimpleNamespace(positions=positions),
        )
    )
    roleKnowledge = Mock()
    roleKnowledge.definitionsList.return_value = ()
    roleKnowledge.weightsLoad.return_value = {"Crossing": 5}
    vocabulary = Mock()
    vocabulary.roles = {
        "advancedWingBack": SimpleNamespace(
            roleID=12,
            displayName="Advanced Wing-Back",
            abbreviations=("AWB",),
            positions=("WBL", "WBR"),
        )
    }

    assessment = SquadAssessmentService(
        database,
        squadModels,
        tacticModels,
        roleKnowledge,
        vocabulary,
    ).assessmentBuild("Test Squad")

    assert assessment is not None
    assert assessment.requiredPositionCount == 2
    assert len(assessment.roles) == 1
    assert assessment.roles[0].roleCode == "advancedWingBack"
    assert assessment.roles[0].positions == ("WB",)
    assert assessment.roles[0].candidates[0].player.name == "Example Player"


def testStoredRoleDefinitionAbbreviationOverridesVocabularyFallback() -> None:
    """The confirmed role definition should control the abbreviation shown in views."""

    player = _player(())
    roleKnowledge = Mock()
    roleKnowledge.weightsLoad.return_value = {}
    vocabulary = Mock()
    vocabulary.roles = {
        "ballPlayingGoalkeeper": SimpleNamespace(
            roleID=2,
            displayName="Ball-Playing Goalkeeper",
            abbreviations=("BPGK", "BGK"),
            positions=("GK",),
        )
    }
    service = SquadAssessmentService(Mock(), Mock(), Mock(), roleKnowledge, vocabulary)
    definition = StoredRoleDefinition(
        roleID=2,
        roleCode="ballPlayingGoalkeeper",
        displayName="Ball-Playing Goalkeeper",
        abbreviations=("BGK",),
        positions=("GK",),
        duties=(),
        behaviours=(),
    )

    assessed = service._roleAssess(
        "ballPlayingGoalkeeper",
        {"GK"},
        {"In Possession"},
        SquadModel(
            "First Team",
            (player,),
            datetime(2026, 8, 15),
            datetime(2026, 8, 15),
            False,
        ),
        definition,
    )

    assert assessed.abbreviation == "BGK"


def testWeakRoleRequiresTwoCandidatesAtOrAboveThreshold() -> None:
    """A calculable but weak backup should still be reported as a depth weakness."""

    first = _player(())
    second = SquadModelPlayer(
        name="Backup Player",
        positions="ST (C)",
        ca="",
        pa="",
        confidence=0.9,
        attributes=(),
    )
    role = RequiredRoleAssessment(
        "channelForward",
        17,
        "Channel Forward",
        "CHF",
        ("STC",),
        ("In Possession",),
        (
            RoleCandidate(first, GenericRoleFit(72.0, None, ())),
            RoleCandidate(second, GenericRoleFit(55.0, None, ())),
        ),
        first.name,
        second.name,
        False,
    )
    roleKnowledge = Mock()
    roleKnowledge.assessmentSettings = {"weakRoleFitThreshold": 60.0}
    service = SquadAssessmentService(
        Mock(),
        Mock(),
        Mock(),
        roleKnowledge,
        Mock(),
    )

    findings = service._weakRolesFind((role,))

    assert len(findings) == 1
    assert "only candidate at 60.0 or above" in findings[0].explanation
