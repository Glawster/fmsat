from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from fmsat.core.config import ConfigurationError
from fmsat.tactics.positionFamily import PositionFamily, positionFamilyFor


@dataclass(frozen=True, slots=True)
class RolePositionFamilyPolicy:
    """Explicit supported position families for known canonical tactic roles."""

    version: int
    roles: dict[str, frozenset[PositionFamily]]

    @classmethod
    def load(cls, path: Path | None = None) -> "RolePositionFamilyPolicy":
        configPath = path or Path(__file__).parents[1] / "config" / "rolePositionFamilies.yaml"
        try:
            with configPath.open(encoding="utf-8") as stream:
                data: Any = yaml.safe_load(stream) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"Unable to load {configPath}: {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigurationError(f"{configPath} must contain a YAML mapping")
        rawRoles = data.get("roles")
        if not isinstance(rawRoles, dict) or not rawRoles:
            raise ConfigurationError("rolePositionFamilies.yaml must contain roles")

        roles: dict[str, frozenset[PositionFamily]] = {}
        for roleCode, rawFamilies in rawRoles.items():
            if not isinstance(rawFamilies, list) or not rawFamilies:
                raise ConfigurationError(
                    f"roles.{roleCode} must contain at least one position family"
                )
            families: set[PositionFamily] = set()
            for value in rawFamilies:
                try:
                    families.add(PositionFamily(str(value)))
                except ValueError as exc:
                    raise ConfigurationError(
                        f"Role {roleCode} references unknown position family {value!r}"
                    ) from exc
            roles[str(roleCode)] = frozenset(families)
        return cls(version=int(data.get("version", 0)), roles=roles)

    def familiesFor(self, roleCode: str) -> frozenset[PositionFamily]:
        """Return configured families for one role, or empty for an unknown role."""

        return self.roles.get(roleCode, frozenset())

    def supports(self, roleCode: str, exactPosition: str) -> bool | None:
        """Validate known role/slot evidence without inventing unknown meaning."""

        supported = self.roles.get(roleCode)
        family = positionFamilyFor(exactPosition)
        if supported is None or family is None:
            return None
        return family in supported


def rolePositionFamilies(roleCode: str) -> frozenset[PositionFamily]:
    """Convenience access to the packaged position-family policy."""

    return RolePositionFamilyPolicy.load().familiesFor(roleCode)


def roleSupportsPosition(roleCode: str, exactPosition: str) -> bool | None:
    """Convenience validation against the packaged position-family policy."""

    return RolePositionFamilyPolicy.load().supports(roleCode, exactPosition)


def cataloguePositionFamily(family: PositionFamily) -> str:
    """Collapse tactical compatibility families into catalogue position lines."""

    if family is PositionFamily.STC:
        return "ST"
    if family in {PositionFamily.AMC, PositionFamily.AMW}:
        return "AM"
    if family in {PositionFamily.MC, PositionFamily.MW}:
        return "M"
    if family is PositionFamily.DM:
        return "DM"
    if family is PositionFamily.WB:
        return "WB"
    if family in {PositionFamily.FB, PositionFamily.DC}:
        return "D"
    return "GK"


def capturedRolePositionFamilies(
    roleCode: str,
    exactPositions: tuple[str, ...],
    policy: RolePositionFamilyPolicy,
) -> tuple[str, ...]:
    """Return unique catalogue families from role policy or captured positions."""

    families = policy.familiesFor(roleCode)
    if not families:
        families = frozenset(
            family
            for position in exactPositions
            if (family := positionFamilyFor(position)) is not None
        )
    return tuple(
        sorted(
            {cataloguePositionFamily(family) for family in families},
            key=("ST", "AM", "M", "DM", "WB", "D", "GK").index,
        )
    )
