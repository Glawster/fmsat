"""Tests for the packaged Generic Role Fit assessment policy."""

from copy import deepcopy

import pytest

from fmsat.core.config import Configuration, ConfigurationError
from fmsat.core.parser import TacticVocabulary


def testPackagedAssessmentPolicyCoversEveryAssessableCanonicalRole() -> None:
    """Every assessable tactic role must have one explicit, valid weight policy."""

    configuration = Configuration()
    weights = configuration.roleAssessmentWeights()
    vocabulary = TacticVocabulary()
    knownAttributes = {attribute.name for attribute in configuration.attributes}

    assert set(weights).issubset(set(vocabulary.roles))
    assert "trackingAttackingMidfielder" in vocabulary.roles
    assert "trackingAttackingMidfielder" not in weights
    assert all(roleWeights for roleWeights in weights.values())
    assert all(
        attribute in knownAttributes and 1 <= weight <= 5
        for roleWeights in weights.values()
        for attribute, weight in roleWeights.items()
    )


def testAssessmentPolicyRejectsMissingCanonicalRole() -> None:
    """A missing assessable role policy must fail rather than leave scoring partially available."""

    configuration = Configuration()
    roleAssessment = deepcopy(configuration.roleAssessment)
    roles = roleAssessment["roles"]
    assert isinstance(roles, dict)
    roles.pop("channelForward")
    configuration.roleAssessment = roleAssessment

    with pytest.raises(ConfigurationError, match="missing=\\['channelForward'\\]"):
        configuration.roleAssessmentWeights()


def testAssessmentPolicyRejectsUnknownRole() -> None:
    """Assessment policy must not silently drift beyond the tactical role catalogue."""

    configuration = Configuration()
    roleAssessment = deepcopy(configuration.roleAssessment)
    roles = roleAssessment["roles"]
    assert isinstance(roles, dict)
    roles["inventedRole"] = {"attributeWeights": {"passing": 5}}
    configuration.roleAssessment = roleAssessment

    with pytest.raises(ConfigurationError, match="unknown=\\['inventedRole'\\]"):
        configuration.roleAssessmentWeights()


def testAssessmentPolicyRejectsUnknownAttribute() -> None:
    """Role weights must only reference attributes captured by the squad model."""

    configuration = Configuration()
    roleAssessment = deepcopy(configuration.roleAssessment)
    roles = roleAssessment["roles"]
    assert isinstance(roles, dict)
    channelForward = roles["channelForward"]
    assert isinstance(channelForward, dict)
    channelForward["attributeWeights"]["mystery_attribute"] = 5
    configuration.roleAssessment = roleAssessment

    with pytest.raises(ConfigurationError, match="mystery_attribute"):
        configuration.roleAssessmentWeights()


def testAssessmentPolicyRejectsInvalidWeight() -> None:
    """The packaged 1-5 scale must be enforced before any player is scored."""

    configuration = Configuration()
    roleAssessment = deepcopy(configuration.roleAssessment)
    roles = roleAssessment["roles"]
    assert isinstance(roles, dict)
    channelForward = roles["channelForward"]
    assert isinstance(channelForward, dict)
    channelForward["attributeWeights"]["pace"] = 6
    configuration.roleAssessment = roleAssessment

    with pytest.raises(ConfigurationError, match="pace"):
        configuration.roleAssessmentWeights()
