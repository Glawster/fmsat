"""Simultaneous tactic-slot depth built from existing Generic Role Fit evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from fmsat.core.squadModel import SquadModelPlayer


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
        states: dict[int, tuple[float, tuple[str | None, ...]]] = {
            0: (0.0, emptyAssignment)
        }

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
            if mask.bit_count() == bestMask.bit_count() and self._stateBetter(
                state, bestState
            ):
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
        """Link IP/OOP positions by durable slot id and assess every squad player."""

        phasePositions = (
            ("IP", tuple(getattr(getattr(tactic, "inPossession", None), "positions", ()))),
            ("OOP", tuple(getattr(getattr(tactic, "outOfPossession", None), "positions", ()))),
        )
        nonEmpty = tuple((phase, positions) for phase, positions in phasePositions if positions)
        if not nonEmpty:
            return ()

        slotIdsByPhase: dict[str, tuple[str, ...]] = {}
        linkageValid = True
        for phase, positions in nonEmpty:
            ids = tuple(str(getattr(position, "slotId", "") or "") for position in positions)
            if not all(ids) or len(set(ids)) != len(ids):
                linkageValid = False
            slotIdsByPhase[phase] = ids

        referencePhase, referencePositions = max(nonEmpty, key=lambda item: len(item[1]))
        referenceIds = slotIdsByPhase.get(referencePhase, ())
        if linkageValid:
            referenceSet = set(referenceIds)
            linkageValid = all(
                len(ids) == len(referenceIds) and set(ids) == referenceSet
                for ids in slotIdsByPhase.values()
            )

        if not linkageValid:
            reason = "Tactic slot linkage is unavailable; complete matching slotId evidence is required"
            return tuple(
                RequiredSlotAssessment(
                    slotId=f"unlinked:{index + 1}",
                    position=self._positionName(position),
                    roles=(),
                    candidates=(),
                    bestCandidate=None,
                    backupCandidate=None,
                    uncovered=True,
                    unavailableReason=reason,
                )
                for index, position in enumerate(referencePositions)
            )

        phaseBySlot = {
            phase: {str(position.slotId): position for position in positions}
            for phase, positions in nonEmpty
        }
        slots: list[RequiredSlotAssessment] = []
        for slotId in referenceIds:
            requirements: list[SlotRoleRequirement] = []
            positionName = ""
            slotReason: str | None = None
            for phase, _positions in nonEmpty:
                position = phaseBySlot[phase][slotId]
                positionName = positionName or self._positionName(position)
                roleCode = getattr(position, "canonicalRole", None)
                role = roleCatalogue.get(roleCode) if roleCode else None
                if roleCode is None:
                    slotReason = f"{phase} roleCode is unavailable"
                    requirements.append(
                        SlotRoleRequirement(phase, None, "Unavailable", "Unavailable")
                    )
                    continue
                if role is None:
                    slotReason = f"{phase} roleCode {roleCode} has no role assessment evidence"
                    requirements.append(
                        SlotRoleRequirement(phase, roleCode, roleCode, roleCode)
                    )
                    continue
                requirements.append(
                    SlotRoleRequirement(
                        phase=phase,
                        roleCode=roleCode,
                        displayName=str(getattr(role, "displayName", roleCode)),
                        abbreviation=str(getattr(role, "abbreviation", roleCode)),
                    )
                )

            candidates = self._candidatesBuild(tuple(requirements), roleCatalogue, slotReason)
            slots.append(
                RequiredSlotAssessment(
                    slotId=slotId,
                    position=positionName,
                    roles=tuple(requirements),
                    candidates=candidates,
                    bestCandidate=None,
                    backupCandidate=None,
                    uncovered=True,
                    unavailableReason=slotReason,
                )
            )
        return tuple(slots)

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
    def _positionName(position: object) -> str:
        """Return canonical position presentation without consulting legacy role enums."""

        canonical = getattr(position, "canonicalPosition", None)
        if canonical:
            return str(canonical)
        identity = getattr(position, "identity", None)
        value = getattr(identity, "value", None)
        return str(value or "Unavailable")
