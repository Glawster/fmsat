"""Simultaneous tactic-slot depth built from existing Generic Role Fit evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from fmsat.core.squadModel import SquadModelPlayer
from fmsat.core.tacticSlots import LinkedTacticSlot, slotsLink


@dataclass(frozen=True, slots=True)
class SlotRoleRequirement:
    """One semantic role required by one tactic slot in one phase."""

    phase: str
    roleCode: str | None
    displayName: str
    abbreviation: str


@dataclass(frozen=True, slots=True)
class SlotRoleFit:
    """One phase-role Generic Role Fit reused by a slot candidate."""

    phase: str
    roleCode: str
    displayName: str
    genericRoleFit: Any


@dataclass(frozen=True, slots=True)
class SlotCandidateAssessment:
    """One player assessed for one simultaneous tactic slot."""

    player: SquadModelPlayer
    score: float | None
    unavailableReason: str | None
    roleFits: tuple[SlotRoleFit, ...]

    @property
    def available(self) -> bool:
        """Return whether the slot score can be reproduced from complete evidence."""

        return self.score is not None


@dataclass(frozen=True, slots=True)
class RequiredSlotAssessment:
    """One simultaneous tactic slot and its unique-player depth outcome."""

    slotId: str
    position: str
    roles: tuple[SlotRoleRequirement, ...]
    candidates: tuple[SlotCandidateAssessment, ...]
    bestCandidate: str | None
    backupCandidate: str | None
    uncovered: bool
    unavailableReason: str | None


class RoleDepthService:
    """Build slot-level depth without introducing Tactical Fit or Best XI logic."""

    def __init__(self, aggregationPolicy: str = "Unavailable") -> None:
        self.aggregationPolicy = aggregationPolicy

    ## depth

    def depthBuild(
        self,
        tactic: object,
        roleCatalogue: Mapping[str, object],
    ) -> tuple[RequiredSlotAssessment, ...]:
        """Return simultaneous slot depth using semantic ``roleCode`` only."""

        slots = self._slotsBuild(tactic, roleCatalogue)
        if not slots:
            return ()

        if self.aggregationPolicy != "phaseMean":
            reason = "Required slot aggregation policy is unavailable"
            return tuple(
                replace(
                    slot,
                    bestCandidate=None,
                    backupCandidate=None,
                    uncovered=True,
                    unavailableReason=reason,
                    candidates=tuple(
                        replace(
                            candidate,
                            score=None,
                            unavailableReason=reason,
                        )
                        for candidate in slot.candidates
                    ),
                )
                for slot in slots
            )

        primary = self._assignmentBuild(slots)
        usedPrimary = {name.casefold() for name in primary.values()}
        backup = self._assignmentBuild(slots, excludedPlayers=usedPrimary)

        return tuple(
            replace(
                slot,
                bestCandidate=primary.get(index),
                backupCandidate=backup.get(index),
                uncovered=primary.get(index) is None,
                unavailableReason=(
                    slot.unavailableReason
                    if primary.get(index) is None and slot.unavailableReason
                    else None
                ),
            )
            for index, slot in enumerate(slots)
        )

    ## assignment

    def _assignmentBuild(
        self,
        slots: tuple[RequiredSlotAssessment, ...],
        excludedPlayers: set[str] | None = None,
    ) -> dict[int, str]:
        """Maximise covered slots, then total score, with each player used once."""

        excluded = excludedPlayers or set()
        players: dict[str, str] = {}
        scoreByPlayerSlot: dict[tuple[str, int], float] = {}
        for slotIndex, slot in enumerate(slots):
            for candidate in slot.candidates:
                if candidate.score is None:
                    continue
                key = candidate.player.name.casefold()
                if key in excluded:
                    continue
                players.setdefault(key, candidate.player.name)
                scoreByPlayerSlot[(key, slotIndex)] = candidate.score

        slotCount = len(slots)
        emptyAssignment: tuple[str | None, ...] = (None,) * slotCount
        states: dict[int, tuple[float, tuple[str | None, ...]]] = {0: (0.0, emptyAssignment)}

        for playerKey in sorted(players):
            currentStates = dict(states)
            for mask, (total, assignment) in states.items():
                for slotIndex in range(slotCount):
                    if mask & (1 << slotIndex):
                        continue
                    score = scoreByPlayerSlot.get((playerKey, slotIndex))
                    if score is None:
                        continue
                    nextMask = mask | (1 << slotIndex)
                    nextAssignment = list(assignment)
                    nextAssignment[slotIndex] = players[playerKey]
                    proposed = (total + score, tuple(nextAssignment))
                    existing = currentStates.get(nextMask)
                    if self._stateBetter(proposed, existing):
                        currentStates[nextMask] = proposed
            states = currentStates

        bestMask = 0
        bestState = states[0]
        for mask, state in states.items():
            if mask.bit_count() > bestMask.bit_count():
                bestMask, bestState = mask, state
                continue
            if mask.bit_count() == bestMask.bit_count() and self._stateBetter(state, bestState):
                bestMask, bestState = mask, state

        return {
            slotIndex: playerName
            for slotIndex, playerName in enumerate(bestState[1])
            if playerName is not None
        }

    @staticmethod
    def _stateBetter(
        proposed: tuple[float, tuple[str | None, ...]],
        existing: tuple[float, tuple[str | None, ...]] | None,
    ) -> bool:
        """Prefer higher total score, then deterministic alphabetical assignment."""

        if existing is None:
            return True
        if proposed[0] != existing[0]:
            return proposed[0] > existing[0]
        proposedKey = tuple((value or "\uffff").casefold() for value in proposed[1])
        existingKey = tuple((value or "\uffff").casefold() for value in existing[1])
        return proposedKey < existingKey

    ## slots

    def _slotsBuild(
        self,
        tactic: object,
        roleCatalogue: Mapping[str, object],
    ) -> tuple[RequiredSlotAssessment, ...]:
        """Map shared position pairing onto slot depth without changing resolution."""

        linked = slotsLink(tactic)
        if not linked:
            return ()

        # Pairing retains every leftover phase position so later Tactic Analysis
        # can count them. Role Depth still shows one assignment row per
        # simultaneous slot and therefore keeps only the larger phase's leftovers.
        referencePhase = self._referencePhase(linked)
        slots: list[RequiredSlotAssessment] = []
        unlinkedIndex = 0
        for item in linked:
            if item.unavailableReason is not None:
                position = item.ipPosition if referencePhase == "IP" else item.oopPosition
                if position is None:
                    continue
                slots.append(
                    self._unlinkedSlotBuild(
                        unlinkedIndex,
                        position,
                        referencePhase,
                        roleCatalogue,
                        item.unavailableReason,
                    )
                )
                unlinkedIndex += 1
                continue
            slots.append(self._linkedSlotBuild(item, roleCatalogue))
        return tuple(slots)

    @staticmethod
    def _referencePhase(linked: tuple[LinkedTacticSlot, ...]) -> str:
        """Prefer the phase that contributed more observed positions; IP when tied."""

        ipCount = sum(slot.ipPosition is not None for slot in linked)
        oopCount = sum(slot.oopPosition is not None for slot in linked)
        return "IP" if ipCount >= oopCount else "OOP"

    def _linkedSlotBuild(
        self,
        item: LinkedTacticSlot,
        roleCatalogue: Mapping[str, object],
    ) -> RequiredSlotAssessment:
        """Resolve catalogue roles for each present phase; omit a missing phase."""

        requirements: list[SlotRoleRequirement] = []
        positionName = ""
        slotReason: str | None = None
        for phase, position in (("IP", item.ipPosition), ("OOP", item.oopPosition)):
            if position is None:
                continue
            positionName = positionName or self._positionName(position)
            requirement, requirementReason = self._requirementFromPosition(
                phase, position, roleCatalogue
            )
            requirements.append(requirement)
            if requirementReason is not None:
                slotReason = requirementReason

        return RequiredSlotAssessment(
            slotId=item.slotId,
            position=positionName,
            roles=tuple(requirements),
            candidates=self._candidatesBuild(tuple(requirements), roleCatalogue, slotReason),
            bestCandidate=None,
            backupCandidate=None,
            uncovered=True,
            unavailableReason=slotReason,
        )

    def _unlinkedSlotBuild(
        self,
        index: int,
        position: object,
        phase: str,
        roleCatalogue: Mapping[str, object],
        reason: str,
    ) -> RequiredSlotAssessment:
        """Keep the observed phase role when pairing evidence is missing.

        Do not invent an IP/OOP partner by ordinal index. Assignment stays
        unavailable until durable slotId or unambiguous spatial evidence exists.
        """

        requirement, _requirementReason = self._requirementFromPosition(
            phase, position, roleCatalogue
        )
        return RequiredSlotAssessment(
            slotId=f"unlinked:{index + 1}",
            position=self._positionName(position),
            roles=(requirement,),
            candidates=(),
            bestCandidate=None,
            backupCandidate=None,
            uncovered=True,
            unavailableReason=reason,
        )

    def _requirementFromPosition(
        self,
        phase: str,
        position: object,
        roleCatalogue: Mapping[str, object],
    ) -> tuple[SlotRoleRequirement, str | None]:
        """Resolve one phase-role from a tactic position without inventing identity."""

        observedAbbreviation = self._observedRoleAbbreviation(position)
        roleCode = self._roleCodeResolve(position, roleCatalogue)
        role = roleCatalogue.get(roleCode) if roleCode else None
        if roleCode is None:
            return (
                SlotRoleRequirement(
                    phase,
                    None,
                    observedAbbreviation or "Unknown role",
                    observedAbbreviation or "Unknown",
                ),
                f"{phase} roleCode is unavailable",
            )
        if role is None:
            return (
                SlotRoleRequirement(
                    phase,
                    roleCode,
                    roleCode,
                    observedAbbreviation or roleCode,
                ),
                f"{phase} roleCode {roleCode} has no role assessment evidence",
            )
        abbreviation = str(getattr(role, "abbreviation", roleCode) or roleCode)
        if observedAbbreviation and abbreviation.casefold() == roleCode.casefold():
            abbreviation = observedAbbreviation
        return (
            SlotRoleRequirement(
                phase=phase,
                roleCode=roleCode,
                displayName=str(getattr(role, "displayName", roleCode)),
                abbreviation=abbreviation,
            ),
            None,
        )

    def _candidatesBuild(
        self,
        requirements: tuple[SlotRoleRequirement, ...],
        roleCatalogue: Mapping[str, object],
        slotReason: str | None,
    ) -> tuple[SlotCandidateAssessment, ...]:
        """Aggregate phase Generic Role Fit with the configured transparent policy."""

        if slotReason is not None or not requirements:
            return ()

        candidateMaps: list[dict[str, object]] = []
        for requirement in requirements:
            if requirement.roleCode is None:
                return ()
            role = roleCatalogue.get(requirement.roleCode)
            if role is None:
                return ()
            candidateMaps.append(
                {
                    candidate.player.name.casefold(): candidate
                    for candidate in getattr(role, "candidates", ())
                }
            )

        playerKeys = sorted(set.intersection(*(set(mapping) for mapping in candidateMaps)))
        results: list[SlotCandidateAssessment] = []
        for playerKey in playerKeys:
            roleFits: list[SlotRoleFit] = []
            missing: list[str] = []
            scores: list[float] = []
            player = None
            for requirement, candidateMap in zip(requirements, candidateMaps):
                candidate = candidateMap[playerKey]
                player = candidate.player
                fit = candidate.genericRoleFit
                roleFits.append(
                    SlotRoleFit(
                        requirement.phase,
                        requirement.roleCode or "Unavailable",
                        requirement.displayName,
                        fit,
                    )
                )
                if fit.score is None:
                    missing.append(
                        f"{requirement.phase} {requirement.displayName}: "
                        f"{fit.unavailableReason or 'Unavailable'}"
                    )
                else:
                    scores.append(float(fit.score))

            if player is None:
                continue
            if missing:
                results.append(
                    SlotCandidateAssessment(
                        player=player,
                        score=None,
                        unavailableReason="; ".join(missing),
                        roleFits=tuple(roleFits),
                    )
                )
                continue
            score = round(sum(scores) / len(scores), 1) if scores else None
            results.append(
                SlotCandidateAssessment(
                    player=player,
                    score=score,
                    unavailableReason=None if score is not None else "Unavailable",
                    roleFits=tuple(roleFits),
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda candidate: (
                    not candidate.available,
                    -(candidate.score if candidate.score is not None else -1.0),
                    candidate.player.name.casefold(),
                ),
            )
        )

    @staticmethod
    def _observedRoleAbbreviation(position: object) -> str:
        """Return the exact role text retained from FM.

        Normal object-model rows may use the generic profile name ``Observed role``
        while retaining the actual FM abbreviation at the start of the profile
        description, for example ``CFD (Observed role)``.  Role-depth analysis must
        consume the same semantic evidence as squad role assessment.
        """

        profile = getattr(position, "roleProfile", None)

        name = str(getattr(profile, "name", "") or "").strip()
        if name.casefold() not in {"", "observed role", "unresolved"}:
            return name

        description = str(getattr(profile, "description", "") or "").strip()
        if description:
            observed = description.split(" (", 1)[0].strip()
            if observed.casefold() not in {"", "observed role", "unresolved"}:
                return observed

        return ""

    @classmethod
    def _roleCodeResolve(
        cls,
        position: object,
        roleCatalogue: Mapping[str, object],
    ) -> str | None:
        """Resolve legacy abbreviation identities to the catalogue without inventing roles."""

        canonical = str(getattr(position, "canonicalRole", "") or "").strip()
        observed = cls._observedRoleAbbreviation(position)
        for candidate in (canonical, observed):
            if not candidate:
                continue
            if candidate in roleCatalogue:
                return candidate
            folded = candidate.casefold()
            matches = [
                roleCode
                for roleCode, role in roleCatalogue.items()
                if str(getattr(role, "abbreviation", "") or "").casefold() == folded
                or str(getattr(role, "displayName", "") or "").casefold() == folded
            ]
            if len(matches) == 1:
                return matches[0]
        if canonical:
            # Exact position codes are eligibility context, never a fallback role
            # identity.  This guards corrupted/legacy mappings such as AMC in the
            # canonicalRole column without rejecting confirmed custom role codes.
            position = cls._positionName(position)
            if canonical.casefold() == position.casefold():
                return None
        return canonical or None

    @staticmethod
    def _positionName(position: object) -> str:
        """Return canonical position presentation without consulting legacy role enums."""

        canonical = getattr(position, "canonicalPosition", None)
        if canonical:
            return str(canonical)
        identity = getattr(position, "identity", None)
        value = getattr(identity, "value", None)
        return str(value or "Unavailable")
