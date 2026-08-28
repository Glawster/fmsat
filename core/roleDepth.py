"""Simultaneous tactic-slot depth built from existing Generic Role Fit evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import dist
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

    _SPATIAL_MAX_DISTANCE = 0.38
    _SPATIAL_AMBIGUITY_MARGIN = 0.05

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
        """Link IP/OOP positions by durable id or unambiguous spatial evidence."""

        phasePositions = (
            ("IP", tuple(getattr(getattr(tactic, "inPossession", None), "positions", ()))),
            ("OOP", tuple(getattr(getattr(tactic, "outOfPossession", None), "positions", ()))),
        )
        nonEmpty = tuple((phase, positions) for phase, positions in phasePositions if positions)
        if not nonEmpty:
            return ()

        slotIdsByPhase: dict[str, tuple[str, ...]] = {}
        uniquePositionsByPhase: dict[str, dict[str, object]] = {}
        for phase, positions in nonEmpty:
            ids = tuple(str(getattr(position, "slotId", "") or "") for position in positions)
            slotIdsByPhase[phase] = ids
            counts = {slotId: ids.count(slotId) for slotId in set(ids) if slotId}
            uniquePositionsByPhase[phase] = {
                slotId: position
                for slotId, position in zip(ids, positions)
                if slotId and counts[slotId] == 1
            }

        referencePhase, referencePositions = max(nonEmpty, key=lambda item: len(item[1]))
        durableIds = set.intersection(
            *(set(positions) for positions in uniquePositionsByPhase.values())
        )
        unlinkedPositions: tuple[object, ...] = ()

        phaseBySlot: dict[str, dict[str, object]]
        if durableIds:
            # A malformed or missing ID on one position must not discard the
            # independently valid durable links for every other tactic slot.
            phaseBySlot = uniquePositionsByPhase
            referenceIds = tuple(
                slotId for slotId in slotIdsByPhase[referencePhase] if slotId in durableIds
            )
            unlinkedPositions = tuple(
                position
                for position in referencePositions
                if str(getattr(position, "slotId", "") or "") not in durableIds
            )
        else:
            spatial = self._spatialPhaseLink(nonEmpty)
            if spatial is None:
                reason = (
                    "Tactic slot linkage is unavailable; complete matching slotId or "
                    "unambiguous spatial evidence is required"
                )
                return tuple(
                    self._unlinkedSlotBuild(
                        index,
                        position,
                        referencePhase,
                        roleCatalogue,
                        reason,
                    )
                    for index, position in enumerate(referencePositions)
                )
            referenceIds, phaseBySlot = spatial

        slots: list[RequiredSlotAssessment] = []
        for slotId in referenceIds:
            requirements: list[SlotRoleRequirement] = []
            positionName = ""
            slotReason: str | None = None
            for phase, _positions in nonEmpty:
                position = phaseBySlot[phase][slotId]
                positionName = positionName or self._positionName(position)
                requirement, requirementReason = self._requirementFromPosition(
                    phase, position, roleCatalogue
                )
                requirements.append(requirement)
                if requirementReason is not None:
                    slotReason = requirementReason

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

        if unlinkedPositions:
            reason = (
                "Tactic slot linkage is unavailable for this position; a matching "
                "durable slotId in every phase is required"
            )
            slots.extend(
                self._unlinkedSlotBuild(
                    index,
                    position,
                    referencePhase,
                    roleCatalogue,
                    reason,
                )
                for index, position in enumerate(unlinkedPositions)
            )
        return tuple(slots)

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

    def _spatialPhaseLink(
        self,
        nonEmpty: tuple[tuple[str, tuple[object, ...]], ...],
    ) -> tuple[tuple[str, ...], dict[str, dict[str, object]]] | None:
        """Recover complete phase linkage only when the global spatial match is unique."""

        if len(nonEmpty) != 2:
            return None
        firstPhase, firstPositions = nonEmpty[0]
        secondPhase, secondPositions = nonEmpty[1]
        if len(firstPositions) != len(secondPositions) or not firstPositions:
            return None
        if any(
            getattr(position, "x", None) is None or getattr(position, "y", None) is None
            for _phase, positions in nonEmpty
            for position in positions
        ):
            return None

        source = tuple(sorted(firstPositions, key=lambda item: (float(item.y), float(item.x))))
        target = tuple(secondPositions)
        count = len(source)
        states: dict[int, list[tuple[float, tuple[int, ...]]]] = {0: [(0.0, ())]}
        for sourceIndex in range(count):
            nextStates: dict[int, list[tuple[float, tuple[int, ...]]]] = {}
            for mask, candidates in states.items():
                for total, assignment in candidates:
                    for targetIndex, targetPosition in enumerate(target):
                        if mask & (1 << targetIndex):
                            continue
                        distance = dist(
                            (float(source[sourceIndex].x), float(source[sourceIndex].y)),
                            (float(targetPosition.x), float(targetPosition.y)),
                        )
                        nextMask = mask | (1 << targetIndex)
                        bucket = nextStates.setdefault(nextMask, [])
                        bucket.append((total + distance, assignment + (targetIndex,)))
                        bucket.sort(key=lambda item: (item[0], item[1]))
                        del bucket[2:]
            states = nextStates

        full = states.get((1 << count) - 1, [])
        if not full:
            return None
        bestCost, bestAssignment = full[0]
        secondCost = full[1][0] if len(full) > 1 else None
        pairDistances = tuple(
            dist(
                (float(source[index].x), float(source[index].y)),
                (float(target[targetIndex].x), float(target[targetIndex].y)),
            )
            for index, targetIndex in enumerate(bestAssignment)
        )
        if max(pairDistances, default=0.0) > self._SPATIAL_MAX_DISTANCE:
            return None
        if secondCost is not None and secondCost - bestCost < self._SPATIAL_AMBIGUITY_MARGIN:
            return None

        slotIds = tuple(f"spatial:{index + 1:02d}" for index in range(count))
        phaseBySlot = {
            firstPhase: {slotId: source[index] for index, slotId in enumerate(slotIds)},
            secondPhase: {
                slotId: target[targetIndex] for slotId, targetIndex in zip(slotIds, bestAssignment)
            },
        }
        return slotIds, phaseBySlot

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
