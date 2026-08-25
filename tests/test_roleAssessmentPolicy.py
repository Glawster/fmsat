"""Tests for the packaged Generic Role Fit assessment policy."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from fmsat.core.config import Configuration, ConfigurationError
from fmsat.core.parser import TacticVocabulary
from fmsat.core.roleAssessmentPolicy import (
    RoleAssessmentPolicyError,
    RoleAssessmentPolicyService,
)


def testPackagedAssessmentPolicyCoversEveryAssessableCanonicalRole() -> None:
    """Every assessable tactic role must have one explicit, valid 0-10 policy."""

    configuration = Configuration()
    weights = configuration.roleAssessmentWeights()
    vocabulary = TacticVocabulary()
    knownAttributes = {attribute.name for attribute in configuration.attributes}

    assert configuration.roleAssessment["weightScale"] == {"minimum": 0, "maximum": 10}
    assert set(weights).issubset(set(vocabulary.roles))
    assert "trackingAttackingMidfielder" in vocabulary.roles
    assert weights["trackingAttackingMidfielder"]
    assert all(roleWeights for roleWeights in weights.values())
    assert all(
        attribute in knownAttributes and 0 <= weight <= 10
        for roleWeights in weights.values()
        for attribute, weight in roleWeights.items()
    )


def testAssessmentPolicyRejectsMissingCanonicalRole() -> None:
    configuration = Configuration()
    roleAssessment = deepcopy(configuration.roleAssessment)
    roles = roleAssessment["roles"]
    assert isinstance(roles, dict)
    roles.pop("channelForward")
    configuration.roleAssessment = roleAssessment

    with pytest.raises(ConfigurationError, match="missing=\\['channelForward'\\]"):
        configuration.roleAssessmentWeights()


def testAssessmentPolicyRejectsUnknownRole() -> None:
    configuration = Configuration()
    roleAssessment = deepcopy(configuration.roleAssessment)
    roles = roleAssessment["roles"]
    assert isinstance(roles, dict)
    roles["inventedRole"] = {"attributeWeights": {"passing": 10}}
    configuration.roleAssessment = roleAssessment

    with pytest.raises(ConfigurationError, match="unknown=\\['inventedRole'\\]"):
        configuration.roleAssessmentWeights()


def testAssessmentPolicyRejectsUnknownAttribute() -> None:
    configuration = Configuration()
    roleAssessment = deepcopy(configuration.roleAssessment)
    roles = roleAssessment["roles"]
    assert isinstance(roles, dict)
    channelForward = roles["channelForward"]
    assert isinstance(channelForward, dict)
    channelForward["attributeWeights"]["mystery_attribute"] = 10
    configuration.roleAssessment = roleAssessment

    with pytest.raises(ConfigurationError, match="mystery_attribute"):
        configuration.roleAssessmentWeights()


def testAssessmentPolicyRejectsInvalidWeight() -> None:
    configuration = Configuration()
    roleAssessment = deepcopy(configuration.roleAssessment)
    roles = roleAssessment["roles"]
    assert isinstance(roles, dict)
    channelForward = roles["channelForward"]
    assert isinstance(channelForward, dict)
    channelForward["attributeWeights"]["pace"] = 11
    configuration.roleAssessment = roleAssessment

    with pytest.raises(ConfigurationError, match="pace"):
        configuration.roleAssessmentWeights()


def _bulkService(tmp_path: Path) -> RoleAssessmentPolicyService:
    return RoleAssessmentPolicyService(
        tmp_path / "roleAssessment.yaml",
        {"channelMidfielder", "trackingWideMidfielder"},
        {"passing", "work_rate", "stamina"},
    )


def testBulkPolicyMigratesLegacyFivePointWeightsToTenPointScale(tmp_path: Path) -> None:
    source = tmp_path / "legacy.yaml"
    source.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "weightScale": {"minimum": 0, "maximum": 5},
                "roles": {
                    "channelMidfielder": {
                        "attributeWeights": {"passing": 5, "work_rate": 4, "stamina": 0}
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    preview = _bulkService(tmp_path).importFile(source)
    saved = yaml.safe_load((tmp_path / "roleAssessment.yaml").read_text(encoding="utf-8"))

    assert preview.migratedLegacyScale is True
    assert saved["weightScale"] == {"minimum": 0, "maximum": 10}
    assert saved["roles"]["channelMidfielder"]["attributeWeights"] == {
        "passing": 10,
        "work_rate": 8,
        "stamina": 0,
    }


def testBulkPolicyPreservesTenPointWeights(tmp_path: Path) -> None:
    source = tmp_path / "current.yaml"
    source.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "weightScale": {"minimum": 0, "maximum": 10},
                "roles": {
                    "trackingWideMidfielder": {
                        "attributeWeights": {"work_rate": 10, "stamina": 9}
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    preview = _bulkService(tmp_path).importFile(source)
    saved = yaml.safe_load((tmp_path / "roleAssessment.yaml").read_text(encoding="utf-8"))

    assert preview.migratedLegacyScale is False
    assert saved["roles"]["trackingWideMidfielder"]["attributeWeights"]["stamina"] == 9


def testBulkPolicyRejectsUnknownRoleWithoutReplacingCurrentPolicy(tmp_path: Path) -> None:
    current = tmp_path / "roleAssessment.yaml"
    current.write_text("sentinel: true\n", encoding="utf-8")
    source = tmp_path / "bad.yaml"
    source.write_text(
        yaml.safe_dump(
            {
                "weightScale": {"minimum": 0, "maximum": 10},
                "roles": {"notARole": {"attributeWeights": {"passing": 8}}},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RoleAssessmentPolicyError, match="Unknown role codes"):
        _bulkService(tmp_path).importFile(source)

    assert current.read_text(encoding="utf-8") == "sentinel: true\n"
