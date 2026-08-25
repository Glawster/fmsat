"""Loading and normalization for canonical tactical vocabulary."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

from ..config import ConfigurationError


@dataclass(frozen=True, slots=True)
class RoleDefinition:
    """A semantic role identity and its allowed tactical context.

    ``code`` is the durable FMSAT identity. ``roleID`` is retained only as a
    legacy/catalogue surrogate for compatibility with older stored data; it
    must never be used to decide which role a piece of OCR evidence represents.
    """

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
        self._packagedRoles = dict(self.roles)
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
        # Semantic codes and full display names are authoritative. Captured OCR can
        # produce an abbreviation already used by a packaged role; retain the
        # packaged interpretation of that shorthand without making the captured
        # role's unique name and code unusable.
        for code, role in self.roles.items():
            for alias in (code, role.displayName):
                self._aliasAdd(values, alias, code, "roles")
        for code, role in self.roles.items():
            for alias in (*role.abbreviations, *role.aliases):
                values.setdefault(self._key(alias), code)
        return self._normalize(observedText, values)

    @staticmethod
    def roleCodeCreate(displayName: str, abbreviation: str = "") -> str:
        """Create a stable lower-camel semantic code from confirmed role evidence."""

        words = re.findall(r"[A-Za-z0-9]+", displayName.strip())
        if not words:
            words = re.findall(r"[A-Za-z0-9]+", abbreviation.strip())
        if not words:
            raise ConfigurationError("A role code requires a display name or abbreviation")
        first, *rest = words
        return first[:1].lower() + first[1:] + "".join(word[:1].upper() + word[1:] for word in rest)

    def canonicalRoleDefinitionGaps(
        self,
        definitions: Iterable[object],
    ) -> tuple[str, ...]:
        """Return OCR-confirmed role definitions absent from tacticalVocabulary.yaml."""

        gaps: set[str] = set()
        for definition in definitions:
            displayName = str(getattr(definition, "displayName", "")).strip()
            abbreviations = tuple(
                str(value).strip()
                for value in getattr(definition, "abbreviations", ())
                if str(value).strip()
            )
            aliases = tuple(value for value in (displayName, *abbreviations) if value)
            if aliases and not any(self.roleNormalize(alias).resolved for alias in aliases):
                gaps.add(displayName or "/".join(abbreviations))
        return tuple(sorted(gaps, key=str.casefold))

    def capturedRolesAdd(self, definitions: Iterable[object]) -> None:
        """Add confirmed user roles using semantic role codes, never numeric IDs.

        Older persisted definitions may contain numeric role IDs or an inferred
        ``roleCode`` that was written while numeric IDs still determined role
        identity. Display name and abbreviation therefore remain the authority
        when loading captured evidence. A stale supplied code is ignored when
        it names an existing role whose aliases do not match the capture.
        """

        for definition in definitions:
            abbreviations = tuple(
                str(value).upper()
                for value in getattr(definition, "abbreviations", ())
                if str(value).strip()
            )
            positions = tuple(str(value) for value in getattr(definition, "positions", ()))
            displayName = str(getattr(definition, "displayName", "")).strip()
            if not abbreviations or not displayName:
                continue

            observedAliases = (displayName, *abbreviations)
            suppliedCode = str(getattr(definition, "roleCode", "") or "").strip()
            canonicalMatches = {
                normalized.value
                for alias in observedAliases
                if (normalized := self.roleNormalize(alias)).resolved
            }
            if len(canonicalMatches) == 1 and not (suppliedCode and suppliedCode not in self.roles):
                continue

            if suppliedCode in self.roles and not any(
                self.roleNormalize(alias).value == suppliedCode for alias in observedAliases
            ):
                suppliedCode = ""
            code = suppliedCode or self.roleCodeCreate(displayName, abbreviations[0])
            if code in self.roles:
                existing = self.roles[code]
                if not any(self.roleNormalize(alias).value == code for alias in observedAliases):
                    raise ConfigurationError(
                        f"Role code {code} is already used by {existing.displayName}"
                    )
                continue

            usedRoleIDs = {role.roleID for role in self.roles.values()}
            runtimeRoleID = max(usedRoleIDs, default=0) + 1
            self.roles[code] = RoleDefinition(
                code=code,
                roleID=runtimeRoleID,
                displayName=displayName,
                abbreviations=abbreviations,
                aliases=(),
                positions=positions,
                duties=(),
            )

    def capturedRolesReplace(self, definitions: Iterable[object]) -> None:
        """Rebuild the effective roles from packaged and currently confirmed roles."""

        self.roles = dict(self._packagedRoles)
        self.capturedRolesAdd(definitions)

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
        key = cls._key(observedText)
        exact = values.get(key)
        if exact is not None:
            return NormalizedValue(exact, observedText)

        # Narrow FM26 overview cards visibly abbreviate long selected values
        # with an ellipsis. Accept that observed prefix only when it identifies
        # one canonical value, so truncated evidence cannot guess between two
        # valid settings.
        if key.endswith("...") or key.endswith("…"):
            prefix = key.rstrip(".…").rstrip()
            matches = {
                canonical
                for alias, canonical in values.items()
                if len(prefix) >= 5 and alias.startswith(prefix)
            }
            if len(matches) == 1:
                return NormalizedValue(matches.pop(), observedText)
        return NormalizedValue(None, observedText)

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
            raise ConfigurationError("Catalogue role IDs must be unique positive integers")
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
