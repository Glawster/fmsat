"""Bulk import/export and migration for Generic Role Fit assessment policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import yaml


class RoleAssessmentPolicyError(RuntimeError):
    """Raised when an assessment-policy file cannot be safely applied."""


@dataclass(frozen=True, slots=True)
class RoleAssessmentPolicyPreview:
    """Validated summary shown before a bulk policy is applied."""

    roleCount: int
    attributeCount: int
    migratedLegacyScale: bool


class RoleAssessmentPolicyService:
    """Validate and atomically replace role weights using semantic role codes."""

    def __init__(
        self,
        policyPath: Path,
        roleCodes: set[str] | frozenset[str],
        attributeIds: set[str] | frozenset[str],
    ) -> None:
        self.policyPath = policyPath.resolve()
        self.roleCodes = frozenset(roleCodes)
        self.attributeIds = frozenset(attributeIds)

    def preview(self, source: Path) -> RoleAssessmentPolicyPreview:
        data, migrated = self._loadAndValidate(source)
        roles = data["roles"]
        return RoleAssessmentPolicyPreview(
            roleCount=len(roles),
            attributeCount=sum(len(role["attributeWeights"]) for role in roles.values()),
            migratedLegacyScale=migrated,
        )

    def importFile(self, source: Path) -> RoleAssessmentPolicyPreview:
        """Validate source fully, then atomically replace the packaged policy."""

        data, migrated = self._loadAndValidate(source)
        temporary = self.policyPath.parent / f".{self.policyPath.name}-{uuid4().hex}.tmp"
        try:
            self.policyPath.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(data, stream, sort_keys=False, allow_unicode=False)
            temporary.replace(self.policyPath)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise RoleAssessmentPolicyError(
                f"Unable to save role assessment policy: {exc}"
            ) from exc
        roles = data["roles"]
        return RoleAssessmentPolicyPreview(
            roleCount=len(roles),
            attributeCount=sum(len(role["attributeWeights"]) for role in roles.values()),
            migratedLegacyScale=migrated,
        )

    def exportFile(self, destination: Path) -> None:
        """Export the current canonical policy without changing it."""

        data, _ = self._loadAndValidate(self.policyPath)
        try:
            destination.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=False),
                encoding="utf-8",
            )
        except OSError as exc:
            raise RoleAssessmentPolicyError(
                f"Unable to export role assessment policy: {exc}"
            ) from exc

    def _loadAndValidate(self, source: Path) -> tuple[dict[str, object], bool]:
        try:
            data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise RoleAssessmentPolicyError(
                f"Unable to read role assessment policy: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise RoleAssessmentPolicyError("Role assessment policy must be a YAML mapping")

        roles = data.get("roles")
        if not isinstance(roles, dict) or not roles:
            raise RoleAssessmentPolicyError(
                "Role assessment policy requires a non-empty roles mapping"
            )

        unknownRoles = sorted(set(roles) - self.roleCodes)
        if unknownRoles:
            raise RoleAssessmentPolicyError(f"Unknown role codes: {unknownRoles}")

        scale = data.get("weightScale")
        legacy = scale in (None, {"minimum": 1, "maximum": 5}, {"minimum": 0, "maximum": 5})
        if not legacy and scale != {"minimum": 0, "maximum": 10}:
            raise RoleAssessmentPolicyError(
                "Weight scale must be 0-10, or an explicit legacy 0/1-5 scale"
            )

        normalizedRoles: dict[str, object] = {}
        for roleCode, roleData in roles.items():
            if not isinstance(roleData, dict):
                raise RoleAssessmentPolicyError(f"Role {roleCode} must be a mapping")
            weights = roleData.get("attributeWeights")
            if not isinstance(weights, dict) or not weights:
                raise RoleAssessmentPolicyError(f"Role {roleCode} requires attributeWeights")
            unknownAttributes = sorted(set(weights) - self.attributeIds)
            if unknownAttributes:
                raise RoleAssessmentPolicyError(
                    f"Unknown attributes for {roleCode}: {unknownAttributes}"
                )
            normalizedWeights: dict[str, int] = {}
            for attribute, value in weights.items():
                if not isinstance(value, int):
                    raise RoleAssessmentPolicyError(
                        f"Weight for {roleCode}.{attribute} must be an integer"
                    )
                if legacy:
                    if not 0 <= value <= 5:
                        raise RoleAssessmentPolicyError(
                            f"Legacy weight for {roleCode}.{attribute} must be between 0 and 5"
                        )
                    value *= 2
                elif not 0 <= value <= 10:
                    raise RoleAssessmentPolicyError(
                        f"Weight for {roleCode}.{attribute} must be between 0 and 10"
                    )
                normalizedWeights[str(attribute)] = value
            normalizedRoles[str(roleCode)] = {
                **{key: value for key, value in roleData.items() if key != "attributeWeights"},
                "attributeWeights": normalizedWeights,
            }

        normalized = dict(data)
        normalized["version"] = max(int(data.get("version", 1)), 2)
        normalized["weightScale"] = {"minimum": 0, "maximum": 10}
        normalized["roles"] = normalizedRoles
        return normalized, legacy
