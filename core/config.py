"""Typed access to FMSAT YAML configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(RuntimeError):
    """Raised when configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class AttributeDefinition:
    """A configurable Football Manager attribute column."""

    name: str
    abbreviation: str
    order: int


class Configuration:
    """Loads application configuration from a replaceable directory."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or Path(__file__).parents[1] / "config"
        self.screens = self._yamlLoad("screens.yaml")
        self.regions = self._yamlLoad("regions.yaml")
        self.tacticExtraction = self._yamlLoad("tacticExtraction.yaml")
        self.roleAssessment = self._yamlLoad("roleAssessment.yaml")
        attributeData = self._yamlLoad("attributes.yaml")
        rawAttributes = attributeData.get("attributes", {})
        if not isinstance(rawAttributes, dict):
            raise ConfigurationError("attributes.yaml must contain an attributes mapping")
        self.attributes = tuple(
            sorted(
                (
                    AttributeDefinition(
                        name=name,
                        abbreviation=str(values["abbreviation"]),
                        order=int(values["order"]),
                    )
                    for name, values in rawAttributes.items()
                ),
                key=lambda item: item.order,
            )
        )

    def confidenceThreshold(self) -> float:
        """Return the row confidence threshold as a value between zero and one."""

        return float(self.screens.get("validation", {}).get("confidence_threshold", 0.95))

    def roleAssessmentSettings(self) -> dict[str, object]:
        """Return traceable analysis settings from the packaged policy."""

        keys = (
            "identity",
            "weakRoleFitThreshold",
            "duplicationFitThreshold",
            "duplicationMinimumPlayers",
            "unusedStrengthThreshold",
            "alternativeRoleLimit",
        )
        result = {key: self.roleAssessment[key] for key in keys}
        result["slotAggregationPolicy"] = self.roleAssessment.get(
            "slotAggregationPolicy",
            "Unavailable",
        )
        return result

    def roleAssessmentWeights(self) -> dict[str, dict[str, int]]:
        """Return validated Generic Role Fit weights by assessable semantic role code.

        Tactical vocabulary can contain recognition-only roles observed in FM screenshots
        before FMSAT has an explicit assessment policy for them. Such roles must still
        normalize correctly during tactic regeneration, but Generic Role Fit remains
        unavailable until a policy is deliberately added. Set ``assessmentRequired: false``
        on those vocabulary entries; every other canonical role must retain complete weights.
        """

        roles = self.roleAssessment.get("roles")
        if not isinstance(roles, dict):
            raise ConfigurationError("roleAssessment.yaml must contain a roles mapping")

        vocabulary = self._yamlLoad("tacticalVocabulary.yaml")
        canonicalRoles = vocabulary.get("roles")
        if not isinstance(canonicalRoles, dict):
            raise ConfigurationError("tacticalVocabulary.yaml must contain a roles mapping")

        configuredCodes = {str(roleCode) for roleCode in roles}
        canonicalCodes = {str(roleCode) for roleCode in canonicalRoles}
        assessableCodes = {
            str(roleCode)
            for roleCode, roleData in canonicalRoles.items()
            if not isinstance(roleData, dict) or roleData.get("assessmentRequired", True) is not False
        }
        missingRoles = sorted(assessableCodes - configuredCodes)
        unknownRoles = sorted(configuredCodes - canonicalCodes)
        if missingRoles or unknownRoles:
            raise ConfigurationError(
                "Generic Role Fit weights must cover every assessable canonical role: "
                f"missing={missingRoles}, unknown={unknownRoles}"
            )

        knownAttributes = {attribute.name for attribute in self.attributes}
        result = {}
        for roleCode in sorted(configuredCodes):
            roleData = roles[roleCode]
            weights = roleData.get("attributeWeights") if isinstance(roleData, dict) else None
            if not isinstance(weights, dict) or not weights:
                raise ConfigurationError(f"Role {roleCode} requires attribute weights")
            unknown = sorted(set(weights) - knownAttributes)
            invalid = {
                name: value
                for name, value in weights.items()
                if not isinstance(value, int) or not 1 <= value <= 5
            }
            if unknown or invalid:
                raise ConfigurationError(
                    f"Invalid role weights for {roleCode}: unknown={unknown}, invalid={invalid}"
                )
            result[roleCode] = {
                str(attribute): int(weight) for attribute, weight in weights.items()
            }
        return result

    def _yamlLoad(self, filename: str) -> dict[str, Any]:
        path = self.directory / filename
        try:
            with path.open(encoding="utf-8") as stream:
                data = yaml.safe_load(stream) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"Unable to load {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigurationError(f"{path} must contain a YAML mapping")
        return data
