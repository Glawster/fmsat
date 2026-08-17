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
    """One confirmed role definition enriched with any known vocabulary metadata."""

    roleID: int
    roleCode: str | None
    displayName: str
    abbreviations: tuple[str, ...]
    positions: tuple[str, ...]
    duties: tuple[str, ...]
    behaviours: tuple[str, ...]


def roleKnowledgeGaps(
    slots: Iterable[FormationSlot],
    definedRoles: Collection[str],
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

    def definitionExists(self, roleCode: str, phase=None) -> bool:
        """Return whether a confirmed user definition exists for a role and phase."""

        path = self._definitionPathFind(roleCode)
        if path is None:
            return False
        if phase is not None:
            if not path.is_file():
                return False
            try:
                content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                return False
            return bool(content.get(phase.value, False))
        return path.is_file()

    def definitionLoad(self, roleCode: str) -> dict[str, object] | None:
        """Load one confirmed definition by stable vocabulary role code."""

        path = self._definitionPathFind(roleCode)
        if path is None:
            return None
        try:
            content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return None
        return content if isinstance(content, dict) else None

    def definitionLoadByRoleID(self, roleID: int) -> dict[str, object] | None:
        """Load one confirmed definition by stable numeric role identity."""

        path = self._definitionPathFindByRoleID(roleID)
        if path is None:
            return None
        try:
            content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return None
        return content if isinstance(content, dict) else None

    def definitionDelete(self, roleID: int) -> tuple[Path, ...]:
        """Delete one confirmed definition and any attached requirement metadata."""

        paths: list[Path] = []
        definitionPath = self._definitionPathFindByRoleID(roleID)
        if definitionPath is not None:
            paths.append(definitionPath)
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
                raise RoleKnowledgeError(f"Unable to delete role definition {roleID}: {exc}") from exc
            deleted.append(path)
        return tuple(deleted)

    def definitionsList(self) -> tuple[StoredRoleDefinition, ...]:
        """Return every confirmed role definition, including user-defined roles."""

        definitions = []
        for path in sorted(self.directory.glob("*.yaml")):
            try:
                content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue
            if not isinstance(content, dict):
                continue
            role = None
            roleID = content.get("roleID")
            if isinstance(roleID, int):
                role = next(
                    (candidate for candidate in self.vocabulary.roles.values() if candidate.roleID == roleID),
                    None,
                )
            else:
                role = self.vocabulary.roles.get(path.stem)
                roleID = role.roleID if role is not None else None
            if not isinstance(roleID, int):
                continue
            displayName = str(
                content.get("displayName") or (role.displayName if role is not None else path.stem)
            )
            abbreviations = self._tupleStrings(content.get("abbreviations")) or (
                role.abbreviations if role is not None else ()
            )
            positions = self._tupleStrings(content.get("positions")) or (
                role.positions if role is not None else ()
            )
            behaviours = self._tupleStrings(content.get("behaviours"))
            definitions.append(
                StoredRoleDefinition(
                    roleID=roleID,
                    roleCode=role.code if role is not None else None,
                    displayName=displayName,
                    abbreviations=abbreviations,
                    positions=positions,
                    duties=role.duties if role is not None else (),
                    behaviours=behaviours,
                )
            )
        return tuple(definitions)

    def weightsLoad(self, roleID: int) -> dict[str, int]:
        """Load FMSAT-owned attribute weights for one stable role identity."""

        path = self.directory.parent / "requirements" / f"role-{roleID:03d}.yaml"
        try:
            content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return self._defaultWeightsLoad(roleID)
        weights = content.get("attributeWeights") if isinstance(content, dict) else None
        if not isinstance(weights, dict):
            return self._defaultWeightsLoad(roleID)
        return {
            str(attribute): int(weight)
            for attribute, weight in weights.items()
            if isinstance(weight, int) and 0 <= weight <= 5
        }

    def _defaultWeightsLoad(self, roleID: int) -> dict[str, int]:
        """Resolve packaged policy through the stable vocabulary role identity."""

        role = next(
            (candidate for candidate in self.vocabulary.roles.values() if candidate.roleID == roleID),
            None,
        )
        return dict(self.defaultWeights.get(role.code, {})) if role is not None else {}

    def importanceLoad(self, roleID: int) -> dict[str, str]:
        """Load explicit assessment importance groups keyed by attribute."""

        path = self.directory.parent / "requirements" / f"role-{roleID:03d}.yaml"
        try:
            content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return {}
        groups = content.get("importanceGroups") if isinstance(content, dict) else None
        if not isinstance(groups, dict):
            return {}
        return {
            str(attribute): str(group)
            for group, attributes in groups.items()
            if group in {"topThree", "important", "niceToHave"} and isinstance(attributes, list)
            for attribute in attributes
        }

    def weightsConfirm(
        self,
        roleID: int,
        weights: dict[str, int],
        importance: dict[str, str] | None = None,
    ) -> Path | None:
        """Atomically save transparent 0–5 assessment weights separately from role facts."""

        importance = self.importanceLoad(roleID) if importance is None else importance
        if not weights and not importance:
            return None
        unknown = sorted((set(weights) | set(importance)) - self.attributeIds)
        if unknown:
            raise RoleKnowledgeError(f"Unknown weighted attributes: {unknown}")
        invalid = {name: value for name, value in weights.items() if not 0 <= value <= 5}
        if invalid:
            raise RoleKnowledgeError(f"Attribute weights must be between 0 and 5: {invalid}")
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
        directory = self.directory.parent / "requirements"
        path = directory / f"role-{roleID:03d}.yaml"
        temporaryPath = directory / f".role-{roleID:03d}-{uuid4().hex}.tmp"
        try:
            directory.mkdir(parents=True, exist_ok=True)
            with temporaryPath.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(
                    {
                        "roleID": roleID,
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
            raise RoleKnowledgeError(f"Unable to save role weights {roleID}: {exc}") from exc
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
        """Return a factual draft when evidence matches the requested knowledge gap."""

        observedPosition = self.vocabulary.positionNormalize(evidence.position)
        if observedPosition.value != expectedPosition:
            raise RoleKnowledgeError(
                f"Expected position {expectedPosition}, but the role profile shows "
                f"{evidence.position or 'an unresolved position'}"
            )
        observedRole = self.vocabulary.roleNormalize(evidence.roleName)
        if observedRole.value != expectedRole and not adoptDetectedRole:
            raise RoleKnowledgeError(
                f"Expected role {expectedRole}, but the role profile shows "
                f"{evidence.roleName or 'an unresolved role'}"
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
        """Atomically write a user-confirmed factual definition as YAML."""

        path = self.directory / f"role-{draft.roleID:03d}.yaml"
        existing: dict[str, object] = {}
        sourcePath = path
        if not sourcePath.exists():
            role = next(
                (role for role in self.vocabulary.roles.values() if role.roleID == draft.roleID),
                None,
            )
            legacyPath = self.directory / f"{role.code}.yaml" if role is not None else None
            if legacyPath is not None and legacyPath.is_file():
                sourcePath = legacyPath
        if sourcePath.exists():
            try:
                loaded = yaml.safe_load(sourcePath.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError) as exc:
                raise RoleKnowledgeError(
                    f"Unable to read role definition {draft.roleID}: {exc}"
                ) from exc
            if not isinstance(loaded, dict):
                raise RoleKnowledgeError(f"Role definition is not a YAML mapping: {draft.roleID}")
            existing = loaded
        if existing.get(draft.phase.value) is True and not replace:
            raise RoleKnowledgeError(
                f"Role definition already contains {draft.phase.value}: {draft.roleID}"
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
        temporaryPath = self.directory / f".{draft.roleID}-{uuid4().hex}.tmp"
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with temporaryPath.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(content, stream, sort_keys=False, allow_unicode=False)
            temporaryPath.replace(path)
        except OSError as exc:
            temporaryPath.unlink(missing_ok=True)
            raise RoleKnowledgeError(
                f"Unable to save role definition {draft.roleID}: {exc}"
            ) from exc
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

    def _definitionPathFind(self, roleCode: str) -> Path | None:
        role = self.vocabulary.roles.get(roleCode)
        if role is None:
            return None
        path = self.directory / f"role-{role.roleID:03d}.yaml"
        if path.is_file():
            return path
        legacyPath = self.directory / f"{roleCode}.yaml"
        return legacyPath if legacyPath.is_file() else None

    def _definitionPathFindByRoleID(self, roleID: int) -> Path | None:
        path = self.directory / f"role-{roleID:03d}.yaml"
        if path.is_file():
            return path
        role = next(
            (candidate for candidate in self.vocabulary.roles.values() if candidate.roleID == roleID),
            None,
        )
        if role is None:
            return None
        legacyPath = self.directory / f"{role.code}.yaml"
        return legacyPath if legacyPath.is_file() else None

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
