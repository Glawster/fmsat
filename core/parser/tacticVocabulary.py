"""Loading and normalization for canonical tactical vocabulary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..config import ConfigurationError


@dataclass(frozen=True, slots=True)
class RoleDefinition:
    """A role identity and its allowed tactical context."""

    code: str
    roleID: int
    displayName: str
    abbreviations: tuple[str, ...]
    aliases: tuple[str, ...]
    positions: tuple[str, ...]
    duties: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NormalizedValue:
    """A canonical value paired with the original observed text."""

    value: str | None
    observedText: str

    @property
    def resolved(self) -> bool:
        """Return whether the observed value matched the vocabulary."""

        return self.value is not None


class TacticVocabulary:
    """Validated canonical positions, roles, duties, and instructions."""

    def __init__(self, path: Path | None = None) -> None:
        configPath = path or Path(__file__).parents[2] / "config" / "tacticalVocabulary.yaml"
        data = self._yamlLoad(configPath)
        self.version = int(data.get("version", 0))
        self.duties = self._aliasMap(data.get("duties"), "duties")
        self.positions = self._aliasMap(data.get("positions"), "positions")
        self.roleIndicators = self._aliasMapOptional(data.get("roleIndicators"), "roleIndicators")
        self.roles = self._rolesLoad(data.get("roles"))
        self.instructions = self._instructionsLoad(data.get("instructions"))
        self._validate()

    def dutyNormalize(self, observedText: str) -> NormalizedValue:
        """Normalize a displayed duty without discarding the OCR text."""

        return self._normalize(observedText, self.duties)

    def instructionNormalize(
        self,
        phase: str,
        category: str,
        observedText: str,
    ) -> NormalizedValue:
        """Normalize one configured instruction value."""

        values = self.instructions.get(phase, {}).get(category, {})
        return self._normalize(observedText, values)

    def positionNormalize(self, observedText: str) -> NormalizedValue:
        """Normalize a position code or alias."""

        return self._normalize(observedText, self.positions)

    def roleNormalize(self, observedText: str) -> NormalizedValue:
        """Normalize a role code, display name, abbreviation, or alias."""

        values: dict[str, str] = {}
        for code, role in self.roles.items():
            for alias in (code, role.displayName, *role.abbreviations, *role.aliases):
                self._aliasAdd(values, alias, code, "roles")
        return self._normalize(observedText, values)

    def roleIndicatorNormalize(self, observedText: str) -> NormalizedValue:
        """Normalize an observed role-performance indicator."""

        return self._normalize(observedText, self.roleIndicators)

    @classmethod
    def _aliasAdd(
        cls,
        aliases: dict[str, str],
        alias: str,
        canonical: str,
        fieldName: str,
    ) -> None:
        key = cls._key(alias)
        if key in aliases and aliases[key] != canonical:
            raise ConfigurationError(f"Duplicate {fieldName} alias: {alias}")
        aliases[key] = canonical

    @classmethod
    def _aliasMap(cls, rawValues: Any, fieldName: str) -> dict[str, str]:
        if not isinstance(rawValues, dict) or not rawValues:
            raise ConfigurationError(
                f"tacticalVocabulary.yaml must contain a non-empty {fieldName} mapping"
            )
        aliases: dict[str, str] = {}
        for canonical, rawAliases in rawValues.items():
            if not isinstance(rawAliases, list):
                raise ConfigurationError(f"{fieldName}.{canonical} aliases must be a list")
            for alias in (str(canonical), *(str(item) for item in rawAliases)):
                cls._aliasAdd(aliases, alias, str(canonical), fieldName)
        return aliases

    @classmethod
    def _aliasMapOptional(cls, rawValues: Any, fieldName: str) -> dict[str, str]:
        if rawValues is None:
            return {}
        return cls._aliasMap(rawValues, fieldName)

    def _instructionsLoad(self, rawInstructions: Any) -> dict[str, dict[str, dict[str, str]]]:
        if not isinstance(rawInstructions, dict):
            raise ConfigurationError("tacticalVocabulary.yaml must contain instructions")
        instructions: dict[str, dict[str, dict[str, str]]] = {}
        for phase, rawCategories in rawInstructions.items():
            if not isinstance(rawCategories, dict):
                raise ConfigurationError(f"instructions.{phase} must be a mapping")
            categories: dict[str, dict[str, str]] = {}
            for category, rawValues in rawCategories.items():
                if not isinstance(rawValues, list):
                    raise ConfigurationError(f"instructions.{phase}.{category} must be a list")
                values: dict[str, list[str]] = {}
                for item in rawValues:
                    if isinstance(item, dict):
                        for canonical, aliases in item.items():
                            if not isinstance(aliases, list):
                                raise ConfigurationError(
                                    f"instructions.{phase}.{category}.{canonical} aliases "
                                    "must be a list"
                                )
                            values[str(canonical)] = [str(alias) for alias in aliases]
                    else:
                        values[str(item)] = []
                categories[str(category)] = self._aliasMap(
                    values, f"instructions.{phase}.{category}"
                )
            instructions[str(phase)] = categories
        return instructions

    @staticmethod
    def _key(value: str) -> str:
        normalized = " ".join(value.casefold().replace("-", " ").split())
        return normalized.replace(" (", "(").replace("( ", "(").replace(" )", ")")

    @classmethod
    def _normalize(cls, observedText: str, values: dict[str, str]) -> NormalizedValue:
        return NormalizedValue(values.get(cls._key(observedText)), observedText)

    def _rolesLoad(self, rawRoles: Any) -> dict[str, RoleDefinition]:
        if not isinstance(rawRoles, dict) or not rawRoles:
            raise ConfigurationError("tacticalVocabulary.yaml must contain roles")
        roles: dict[str, RoleDefinition] = {}
        for code, values in rawRoles.items():
            if not isinstance(values, dict):
                raise ConfigurationError(f"roles.{code} must be a mapping")
            try:
                roles[str(code)] = RoleDefinition(
                    code=str(code),
                    roleID=int(values["roleID"]),
                    displayName=str(values["displayName"]),
                    abbreviations=tuple(str(item).upper() for item in values["abbreviations"]),
                    aliases=tuple(str(item) for item in values.get("aliases", [])),
                    positions=tuple(str(item) for item in values["positions"]),
                    duties=tuple(str(item) for item in values["duties"]),
                )
            except (KeyError, TypeError) as exc:
                raise ConfigurationError(f"roles.{code} is incomplete") from exc
        return roles

    def _validate(self) -> None:
        positionCodes = set(self.positions.values())
        dutyCodes = set(self.duties.values())
        roleIDs = [role.roleID for role in self.roles.values()]
        if any(roleID < 1 for roleID in roleIDs) or len(roleIDs) != len(set(roleIDs)):
            raise ConfigurationError("Role IDs must be unique positive integers")
        for role in self.roles.values():
            unknownPositions = set(role.positions) - positionCodes
            unknownDuties = set(role.duties) - dutyCodes
            if unknownPositions:
                raise ConfigurationError(
                    f"Role {role.code} references unknown positions: {sorted(unknownPositions)}"
                )
            if unknownDuties:
                raise ConfigurationError(
                    f"Role {role.code} references unknown duties: {sorted(unknownDuties)}"
                )

    @staticmethod
    def _yamlLoad(path: Path) -> dict[str, Any]:
        try:
            with path.open(encoding="utf-8") as stream:
                data = yaml.safe_load(stream) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"Unable to load {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigurationError(f"{path} must contain a YAML mapping")
        return data
