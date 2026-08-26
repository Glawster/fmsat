"""Role knowledge gaps, evidence verification, and confirmed YAML storage."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import yaml

from .parser import (
    FormationSlot,
    RoleDefinitionDraft,
    RoleKnowledgeGap,
    RoleProfileEvidence,
    TacticVocabulary,
)


class RoleKnowledgeError(RuntimeError):
    """Raised when role evidence cannot safely alter the knowledge base."""


@dataclass(frozen=True, slots=True)
class StoredRoleDefinition:
    """One confirmed role definition keyed by stable semantic role code."""

    roleCode: str
    displayName: str
    abbreviations: tuple[str, ...]
    positions: tuple[str, ...]
    duties: tuple[str, ...]
    behaviours: tuple[str, ...]
    roleID: int | None = None


def roleKnowledgeGaps(
    slots: Iterable[FormationSlot], definedRoles: Collection[str]
) -> tuple[RoleKnowledgeGap, ...]:
    """Return one gap per missing role and position, retaining affected slots."""
    slotIds: dict[tuple[str, str], list[str]] = defaultdict(list)
    for slot in slots:
        if slot.role is None or slot.position is None or slot.role in definedRoles:
            continue
        slotIds[(slot.role, slot.position)].append(slot.slotId)
    return tuple(
        RoleKnowledgeGap(role, position, tuple(sorted(ids)))
        for (role, position), ids in sorted(slotIds.items())
    )


class RoleKnowledgeService:
    """Verify role-profile evidence and atomically save confirmed definitions."""

    def __init__(
        self,
        directory: Path,
        vocabulary: TacticVocabulary,
        attributeIds: Collection[str],
        defaultWeights: dict[str, dict[str, int]] | None = None,
        assessmentSettings: dict[str, object] | None = None,
    ) -> None:
        self.directory = directory.resolve()
        self.vocabulary = vocabulary
        self.attributeIds = frozenset(attributeIds)
        self.defaultWeights = defaultWeights or {}
        self.assessmentSettings = assessmentSettings or {}
        self._vocabularyRefresh()

    def definitionExists(self, roleCode: str, phase=None) -> bool:
        path = self._definitionPathFind(roleCode)
        if path is None:
            return False
        if phase is not None:
            try:
                content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                return False
            return bool(content.get(phase.value, False)) if isinstance(content, dict) else False
        return path.is_file()

    def definitionLoad(self, roleCode: str) -> dict[str, object] | None:
        path = self._definitionPathFind(roleCode)
        if path is None:
            return None
        try:
            content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return None
        return content if isinstance(content, dict) else None

    def definitionLoadByRoleID(self, roleID: int) -> dict[str, object] | None:
        path = self._definitionPathFindByRoleID(roleID)
        if path is None:
            return None
        try:
            content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return None
        return content if isinstance(content, dict) else None

    def definitionDelete(self, roleID: int) -> tuple[Path, ...]:
        paths: list[Path] = []
        definitionPath = self._definitionPathFindByRoleID(roleID)
        if definitionPath is not None:
            paths.append(definitionPath)
            roleCode = self._roleCodeFromPath(definitionPath)
            if roleCode:
                semanticRequirements = self.directory.parent / "requirements" / f"{roleCode}.yaml"
                if semanticRequirements.is_file():
                    paths.append(semanticRequirements)
        requirementsPath = self.directory.parent / "requirements" / f"role-{roleID:03d}.yaml"
        if requirementsPath.is_file():
            paths.append(requirementsPath)
        if not paths:
            raise RoleKnowledgeError(f"Role definition does not exist: {roleID}")
        deleted: list[Path] = []
        for path in dict.fromkeys(paths):
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                raise RoleKnowledgeError(
                    f"Unable to delete role definition {roleID}: {exc}"
                ) from exc
            deleted.append(path)
        self._vocabularyRefresh()
        return tuple(deleted)

    def definitionsList(self) -> tuple[StoredRoleDefinition, ...]:
        definitions = []
        for path in sorted(self.directory.glob("*.yaml")):
            try:
                content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue
            if not isinstance(content, dict):
                continue
            displayName = str(content.get("displayName") or path.stem).strip()
            abbreviations = self._tupleStrings(content.get("abbreviations"))
            roleCode = self._roleCodeResolve(content, path, displayName, abbreviations)
            role = self.vocabulary.roles.get(roleCode)
            if role is not None:
                displayName = str(content.get("displayName") or role.displayName)
                abbreviations = abbreviations or role.abbreviations
            positions = self._tupleStrings(content.get("positions")) or (
                role.positions if role is not None else ()
            )
            behaviours = self._tupleStrings(content.get("behaviours"))
            roleID = content.get("roleID")
            definitions.append(
                StoredRoleDefinition(
                    roleCode=roleCode,
                    displayName=displayName,
                    abbreviations=abbreviations,
                    positions=positions,
                    duties=role.duties if role is not None else (),
                    behaviours=behaviours,
                    roleID=roleID if isinstance(roleID, int) else None,
                )
            )
        return tuple(definitions)

    def _vocabularyRefresh(self) -> None:
        """Synchronize confirmed definitions into the shared runtime vocabulary."""

        self.vocabulary.capturedRolesReplace(self.definitionsList())

    def weightsLoad(self, roleIdentity: str | int) -> dict[str, int]:
        roleCode = self._roleCodeFromIdentity(roleIdentity)
        if roleCode is not None:
            path = self.directory.parent / "requirements" / f"{roleCode}.yaml"
            weights = self._weightsFromPath(path)
            if weights:
                return weights
            role = self.vocabulary.roles.get(roleCode)
            if role is not None:
                legacy = self.directory.parent / "requirements" / f"role-{role.roleID:03d}.yaml"
                weights = self._weightsFromPath(legacy)
                if weights:
                    return weights
            return dict(self.defaultWeights.get(roleCode, {}))
        if isinstance(roleIdentity, int):
            legacy = self.directory.parent / "requirements" / f"role-{roleIdentity:03d}.yaml"
            weights = self._weightsFromPath(legacy)
            if weights is not None:
                return weights
        return {}

    def importanceLoad(self, roleIdentity: str | int) -> dict[str, str]:
        paths: list[Path] = []
        roleCode = self._roleCodeFromIdentity(roleIdentity)
        if roleCode is not None:
            paths.append(self.directory.parent / "requirements" / f"{roleCode}.yaml")
            role = self.vocabulary.roles.get(roleCode)
            if role is not None:
                paths.append(
                    self.directory.parent / "requirements" / f"role-{role.roleID:03d}.yaml"
                )
        elif isinstance(roleIdentity, int):
            paths.append(self.directory.parent / "requirements" / f"role-{roleIdentity:03d}.yaml")
        for path in paths:
            try:
                content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue
            groups = content.get("importanceGroups") if isinstance(content, dict) else None
            if not isinstance(groups, dict):
                continue
            return {
                str(attribute): str(group)
                for group, attributes in groups.items()
                if group in {"topThree", "important", "niceToHave"} and isinstance(attributes, list)
                for attribute in attributes
            }
        return {}

    def weightsConfirm(
        self,
        roleIdentity: str | int,
        weights: dict[str, int],
        importance: dict[str, str] | None = None,
    ) -> Path | None:
        importance = self.importanceLoad(roleIdentity) if importance is None else importance
        if not weights and not importance:
            return None
        unknown = sorted((set(weights) | set(importance)) - self.attributeIds)
        if unknown:
            raise RoleKnowledgeError(f"Unknown weighted attributes: {unknown}")
        invalid = {name: value for name, value in weights.items() if not 0 <= value <= 10}
        if invalid:
            raise RoleKnowledgeError(f"Attribute weights must be between 0 and 10: {invalid}")
        invalidGroups = {
            name: group
            for name, group in importance.items()
            if group not in {"topThree", "important", "niceToHave"}
        }
        if invalidGroups:
            raise RoleKnowledgeError(f"Unknown importance groups: {invalidGroups}")
        topThree = [name for name, group in importance.items() if group == "topThree"]
        if len(topThree) > 3:
            raise RoleKnowledgeError("Top three may contain at most three attributes")
        roleCode = self._roleCodeFromIdentity(roleIdentity)
        directory = self.directory.parent / "requirements"
        if roleCode is not None:
            path = directory / f"{roleCode}.yaml"
            identityContent: dict[str, object] = {"roleCode": roleCode}
        elif isinstance(roleIdentity, int):
            path = directory / f"role-{roleIdentity:03d}.yaml"
            identityContent = {"roleID": roleIdentity}
        else:
            raise RoleKnowledgeError(f"Unknown role identity: {roleIdentity}")
        temporaryPath = directory / f".{path.stem}-{uuid4().hex}.tmp"
        try:
            directory.mkdir(parents=True, exist_ok=True)
            with temporaryPath.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(
                    {
                        **identityContent,
                        "attributeWeights": weights,
                        "importanceGroups": {
                            group: [
                                name for name, assigned in importance.items() if assigned == group
                            ]
                            for group in ("topThree", "important", "niceToHave")
                        },
                    },
                    stream,
                    sort_keys=False,
                )
            temporaryPath.replace(path)
        except OSError as exc:
            temporaryPath.unlink(missing_ok=True)
            raise RoleKnowledgeError(f"Unable to save role weights {roleIdentity}: {exc}") from exc
        return path

    def evidenceVerify(
        self,
        evidence: RoleProfileEvidence,
        expectedPosition: str,
        expectedRole: str,
        *,
        adoptDetectedRole: bool = False,
        supportedPositions: tuple[str, ...] = (),
    ) -> RoleDefinitionDraft:
        observedPosition = self.vocabulary.positionNormalize(evidence.position)
        if observedPosition.value != expectedPosition:
            raise RoleKnowledgeError(
                f"Expected position {expectedPosition}, but the role profile shows {evidence.position or 'an unresolved position'}"
            )
        observedRole = self.vocabulary.roleNormalize(evidence.roleName)
        if observedRole.value != expectedRole and not adoptDetectedRole:
            raise RoleKnowledgeError(
                f"Expected role {expectedRole}, but the role profile shows {evidence.roleName or 'an unresolved role'}"
            )
        if not evidence.keyAttributes:
            raise RoleKnowledgeError("The role profile has no confirmed key attributes")
        if evidence.phase is None:
            raise RoleKnowledgeError("The role profile phase is unresolved")
        unknownAttributes = sorted(set(evidence.keyAttributes) - self.attributeIds)
        if unknownAttributes:
            raise RoleKnowledgeError(f"Unknown key attributes: {unknownAttributes}")
        role = self.vocabulary.roles.get(observedRole.value) if observedRole.resolved else None
        if role is not None and expectedPosition not in role.positions:
            raise RoleKnowledgeError(
                f"Role {role.code} is not configured for position {expectedPosition}"
            )
        positions = []
        for position in supportedPositions:
            normalizedPosition = self.vocabulary.positionNormalize(position)
            if not normalizedPosition.resolved:
                raise RoleKnowledgeError(f"Unknown supported position: {position}")
            positions.append(normalizedPosition.value)
        positions = list(dict.fromkeys(positions))
        if positions and expectedPosition not in positions:
            raise RoleKnowledgeError(
                f"Supported positions must include the detected position {expectedPosition}"
            )
        if role is not None:
            unsupported = sorted(set(positions) - set(role.positions))
            if unsupported:
                raise RoleKnowledgeError(
                    f"Role {role.code} does not support positions: {unsupported}"
                )
        roleID = role.roleID if role is not None else self._roleIDNext()
        abbreviations = (
            (evidence.abbreviation.upper(),)
            if evidence.abbreviation
            else role.abbreviations if role is not None else ()
        )
        return RoleDefinitionDraft(
            roleID=roleID,
            displayName=role.displayName if role is not None else evidence.roleName,
            phase=evidence.phase,
            abbreviations=abbreviations,
            positions=(
                tuple(positions)
                if positions
                else role.positions if role is not None else (expectedPosition,)
            ),
            description=evidence.description,
            behaviours=evidence.behaviours,
            keyAttributes=evidence.keyAttributes,
            playerInstructions=evidence.playerInstructions,
            sourceImport=evidence.sourceImport,
        )

    def definitionConfirm(self, draft: RoleDefinitionDraft, *, replace: bool = False) -> Path:
        normalized = self.vocabulary.roleNormalize(draft.displayName)
        roleCode = (
            normalized.value
            if normalized.resolved
            else self.vocabulary.roleCodeCreate(
                draft.displayName, draft.abbreviations[0] if draft.abbreviations else ""
            )
        )
        existingPath = self._definitionPathFind(roleCode)
        path = existingPath or self.directory / f"role-{draft.roleID:03d}.yaml"
        existing: dict[str, object] = {}
        if path.exists():
            try:
                loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError) as exc:
                raise RoleKnowledgeError(
                    f"Unable to read role definition {roleCode}: {exc}"
                ) from exc
            if not isinstance(loaded, dict):
                raise RoleKnowledgeError(f"Role definition is not a YAML mapping: {roleCode}")
            existing = loaded
        if existing.get(draft.phase.value) is True and not replace:
            raise RoleKnowledgeError(
                f"Role definition already contains {draft.phase.value}: {roleCode}"
            )
        provenance = existing.get("provenance", {})
        if not isinstance(provenance, dict):
            provenance = {}
        sources = provenance.get("sources", {})
        if not isinstance(sources, dict):
            sources = {}
        legacySource = provenance.get("sourceImport")
        if legacySource and "inPossession" not in sources:
            sources["inPossession"] = legacySource
        sources[draft.phase.value] = draft.sourceImport
        content: dict[str, object] = {
            "roleCode": roleCode,
            "roleID": draft.roleID,
            "displayName": draft.displayName,
            "inPossession": draft.phase.value == "inPossession"
            or bool(existing.get("inPossession", False)),
            "outOfPossession": draft.phase.value == "outOfPossession"
            or bool(existing.get("outOfPossession", False)),
            "abbreviations": self._abbreviationsMerge(
                existing.get("abbreviations"), draft.abbreviations
            ),
            "positions": self._valuesMerge(existing.get("positions"), draft.positions),
            "description": draft.description or existing.get("description"),
            "behaviours": self._valuesMerge(existing.get("behaviours"), draft.behaviours),
            "keyAttributes": list(draft.keyAttributes),
            "playerInstructions": self._valuesMerge(
                existing.get("playerInstructions"), draft.playerInstructions
            ),
            "provenance": {"sources": sources, "reviewState": "confirmed"},
        }
        temporaryPath = self.directory / f".{roleCode}-{uuid4().hex}.tmp"
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with temporaryPath.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(content, stream, sort_keys=False, allow_unicode=False)
            temporaryPath.replace(path)
        except OSError as exc:
            temporaryPath.unlink(missing_ok=True)
            raise RoleKnowledgeError(f"Unable to save role definition {roleCode}: {exc}") from exc
        self._vocabularyRefresh()
        return path

    def _roleIDNext(self) -> int:
        roleIDs = {role.roleID for role in self.vocabulary.roles.values()}
        if self.directory.is_dir():
            for path in self.directory.glob("*.yaml"):
                try:
                    content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                except (OSError, yaml.YAMLError):
                    continue
                if isinstance(content, dict) and isinstance(content.get("roleID"), int):
                    roleIDs.add(content["roleID"])
        return max(roleIDs, default=0) + 1

    def _roleCodeResolve(
        self,
        content: dict[str, object],
        path: Path,
        displayName: str,
        abbreviations: tuple[str, ...],
    ) -> str:
        explicit = content.get("roleCode")
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip()
        for alias in (displayName, *abbreviations):
            normalized = self.vocabulary.roleNormalize(alias)
            if normalized.resolved:
                return str(normalized.value)
        if path.stem in self.vocabulary.roles:
            return path.stem
        return self.vocabulary.roleCodeCreate(
            displayName, abbreviations[0] if abbreviations else ""
        )

    def _roleCodeFromPath(self, path: Path) -> str | None:
        try:
            content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return None
        if not isinstance(content, dict):
            return None
        displayName = str(content.get("displayName") or path.stem).strip()
        abbreviations = self._tupleStrings(content.get("abbreviations"))
        return self._roleCodeResolve(content, path, displayName, abbreviations)

    def _roleCodeFromIdentity(self, roleIdentity: str | int) -> str | None:
        if isinstance(roleIdentity, str) and roleIdentity.strip():
            raw = roleIdentity.strip()
            if raw in self.vocabulary.roles:
                return raw
            normalized = self.vocabulary.roleNormalize(raw)
            return str(normalized.value) if normalized.resolved else raw
        if isinstance(roleIdentity, int):
            role = next(
                (
                    candidate
                    for candidate in self.vocabulary.roles.values()
                    if candidate.roleID == roleIdentity
                ),
                None,
            )
            return role.code if role is not None else None
        return None

    def _definitionPathFind(self, roleCode: str) -> Path | None:
        semanticPath = self.directory / f"{roleCode}.yaml"
        if semanticPath.is_file():
            return semanticPath
        if not self.directory.is_dir():
            return None
        for path in sorted(self.directory.glob("*.yaml")):
            if self._roleCodeFromPath(path) == roleCode:
                return path
        return None

    def _definitionPathFindByRoleID(self, roleID: int) -> Path | None:
        path = self.directory / f"role-{roleID:03d}.yaml"
        if path.is_file():
            return path
        if not self.directory.is_dir():
            return None
        for candidate in self.directory.glob("*.yaml"):
            try:
                content = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue
            if isinstance(content, dict) and content.get("roleID") == roleID:
                return candidate
        return None

    def _weightsFromPath(self, path: Path) -> dict[str, int] | None:
        try:
            content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return None
        weights = content.get("attributeWeights") if isinstance(content, dict) else None
        if not isinstance(weights, dict):
            return None
        parsed = {
            str(attribute): int(weight)
            for attribute, weight in weights.items()
            if isinstance(weight, int) and 0 <= weight <= 10
        }
        return parsed

    @staticmethod
    def _tupleStrings(value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(str(item) for item in value)

    @staticmethod
    def _abbreviationsMerge(existing: object, added: tuple[str, ...]) -> list[str]:
        values = RoleKnowledgeService._valuesMerge(existing, added)
        return list(dict.fromkeys(value.upper() for value in values))

    @staticmethod
    def _valuesMerge(existing: object, added: tuple[str, ...]) -> list[str]:
        values = existing if isinstance(existing, list) else []
        return list(dict.fromkeys([*(str(value) for value in values), *added]))
