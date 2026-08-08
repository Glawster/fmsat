"""Role knowledge gaps, evidence verification, and confirmed YAML storage."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Collection, Iterable
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
    ) -> None:
        self.directory = directory.resolve()
        self.vocabulary = vocabulary
        self.attributeIds = frozenset(attributeIds)

    def definitionExists(self, roleId: str, phase=None) -> bool:
        """Return whether a confirmed user definition exists for a role and phase."""

        path = self.directory / f"{roleId}.yaml"
        if phase is not None:
            if not path.is_file():
                return False
            try:
                content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                return False
            return bool(content.get(phase.value, False))
        return path.is_file()

    def evidenceVerify(
        self,
        evidence: RoleProfileEvidence,
        expectedPosition: str,
        expectedRole: str,
        *,
        adoptDetectedRole: bool = False,
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
        roleId = role.code if role is not None else self._identifier(evidence.roleName)
        abbreviations = (
            (evidence.abbreviation.upper(),)
            if evidence.abbreviation
            else role.abbreviations if role is not None else ()
        )
        return RoleDefinitionDraft(
            id=roleId,
            displayName=role.displayName if role is not None else evidence.roleName,
            phase=evidence.phase,
            abbreviations=abbreviations,
            positions=(expectedPosition,),
            description=evidence.description,
            behaviours=evidence.behaviours,
            keyAttributes=evidence.keyAttributes,
            playerInstructions=evidence.playerInstructions,
            sourceImport=evidence.sourceImport,
        )

    @staticmethod
    def _identifier(value: str) -> str:
        words = re.findall(r"[A-Za-z0-9]+", value)
        if not words:
            raise RoleKnowledgeError("The detected role name is empty")
        return words[0].casefold() + "".join(word.title() for word in words[1:])

    def definitionConfirm(self, draft: RoleDefinitionDraft, *, replace: bool = False) -> Path:
        """Atomically write a user-confirmed factual definition as YAML."""

        path = self.directory / f"{draft.id}.yaml"
        existing: dict[str, object] = {}
        if path.exists():
            try:
                loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError) as exc:
                raise RoleKnowledgeError(
                    f"Unable to read role definition {draft.id}: {exc}"
                ) from exc
            if not isinstance(loaded, dict):
                raise RoleKnowledgeError(f"Role definition is not a YAML mapping: {draft.id}")
            existing = loaded
        if existing.get(draft.phase.value) is True and not replace:
            raise RoleKnowledgeError(
                f"Role definition already contains {draft.phase.value}: {draft.id}"
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
            "id": draft.id,
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
            "keyAttributes": self._valuesMerge(existing.get("keyAttributes"), draft.keyAttributes),
            "playerInstructions": self._valuesMerge(
                existing.get("playerInstructions"), draft.playerInstructions
            ),
            "provenance": {"sources": sources, "reviewState": "confirmed"},
        }
        temporaryPath = self.directory / f".{draft.id}-{uuid4().hex}.tmp"
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with temporaryPath.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(content, stream, sort_keys=False, allow_unicode=False)
            temporaryPath.replace(path)
        except OSError as exc:
            temporaryPath.unlink(missing_ok=True)
            raise RoleKnowledgeError(f"Unable to save role definition {draft.id}: {exc}") from exc
        return path

    @staticmethod
    def _abbreviationsMerge(existing: object, added: tuple[str, ...]) -> list[str]:
        values = RoleKnowledgeService._valuesMerge(existing, added)
        return list(dict.fromkeys(value.upper() for value in values))

    @staticmethod
    def _valuesMerge(existing: object, added: tuple[str, ...]) -> list[str]:
        values = existing if isinstance(existing, list) else []
        return list(dict.fromkeys([*(str(value) for value in values), *added]))
