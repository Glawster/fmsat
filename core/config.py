"""Typed access to FMSAT YAML configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml


class ConfigurationError(RuntimeError):
    """Raised when configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class AttributeDefinition:
    """A configurable Football Manager attribute column."""

    name: str
    abbreviation: str
    order: int
    active: bool = True


class AttributeConfigurationService:
    """Persist whether configured FM attributes participate in FMSAT."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()

    def definitionsLoad(self) -> tuple[AttributeDefinition, ...]:
        """Return all configured attributes, including currently inactive ones."""

        try:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"Unable to load {self.path}: {exc}") from exc
        rawAttributes = data.get("attributes") if isinstance(data, dict) else None
        if not isinstance(rawAttributes, dict):
            raise ConfigurationError("attributes.yaml must contain an attributes mapping")
        return tuple(
            sorted(
                (
                    AttributeDefinition(
                        name=str(name),
                        abbreviation=str(values["abbreviation"]),
                        order=int(values["order"]),
                        active=bool(values.get("active", True)),
                    )
                    for name, values in rawAttributes.items()
                    if isinstance(values, dict)
                ),
                key=lambda item: item.order,
            )
        )

    def activeSet(self, attributeName: str, active: bool) -> tuple[AttributeDefinition, ...]:
        """Atomically toggle one attribute without disturbing its other configuration."""

        try:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"Unable to load {self.path}: {exc}") from exc
        rawAttributes = data.get("attributes") if isinstance(data, dict) else None
        if not isinstance(rawAttributes, dict):
            raise ConfigurationError("attributes.yaml must contain an attributes mapping")
        values = rawAttributes.get(attributeName)
        if not isinstance(values, dict):
            raise ConfigurationError(f"Unknown configured attribute: {attributeName}")
        values["active"] = bool(active)

        temporary = self.path.parent / f".{self.path.name}-{uuid4().hex}.tmp"
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(data, stream, sort_keys=False, allow_unicode=False)
            temporary.replace(self.path)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise ConfigurationError(f"Unable to save {self.path}: {exc}") from exc
        return self.definitionsLoad()


class Configuration:
    """Loads application configuration from a replaceable directory."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or Path(__file__).parents[1] / "config"
        self.screens = self._yamlLoad("screens.yaml")
        self.regions = self._yamlLoad("regions.yaml")
        self.tacticExtraction = self._yamlLoad("tacticExtraction.yaml")
        self.roleAssessment = self._yamlLoad("roleAssessment.yaml")
        self.attributeService = AttributeConfigurationService(self.directory / "attributes.yaml")
        self.attributes = self.attributeService.definitionsLoad()

    @property
    def activeAttributes(self) -> tuple[AttributeDefinition, ...]:
        """Return only attributes currently participating in normal FMSAT workflows."""

        return tuple(attribute for attribute in self.attributes if attribute.active)

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
        """Return validated 0-10 Generic Role Fit weights by semantic role code."""

        scale = self.roleAssessment.get("weightScale")
        if scale != {"minimum": 0, "maximum": 10}:
            raise ConfigurationError(
                "roleAssessment.yaml must declare weightScale minimum 0 and maximum 10"
            )

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
            if not isinstance(roleData, dict)
            or roleData.get("assessmentRequired", True) is not False
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
                if not isinstance(value, int) or not 0 <= value <= 10
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