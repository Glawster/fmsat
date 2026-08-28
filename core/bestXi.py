"""Global Best XI assignment from existing role-fit evidence.

The optimiser deliberately consumes already-calculated Generic Role Fit presentation
values.  It does not recalculate player attributes, infer missing evidence, or alter
Required Role Depth.  Best XI is a separate whole-team assignment problem.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Iterable

from fmsat.tactics.positionFamily import playerPositionFamilies, positionFamilyFor


@dataclass(frozen=True, slots=True)
class BestXiSlotCandidate:
    """One player who has complete role-fit evidence for one tactic slot."""

    playerName: str
    score: float
    familiar: bool
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BestXiSelection:
    """One selected unique player for one simultaneous tactic slot."""

    slotIndex: int
    playerName: str
    score: float
    familiar: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class BestXiAssignment:
    """Globally optimised Best XI outcome."""

    selections: tuple[BestXiSelection, ...]
    coveredSlots: int
    requiredSlots: int
    totalScore: float
    weakestScore: float | None
    evidenceAvailable: bool

    def selectionFor(self, slotIndex: int) -> BestXiSelection | None:
        """Return the selected player for one displayed slot index."""

        return next(
            (selection for selection in self.selections if selection.slotIndex == slotIndex),
            None,
        )


@dataclass(frozen=True, slots=True)
class _State:
    totalScore: float
    weakestScore: float
    assignments: tuple[str | None, ...]
    scores: tuple[float | None, ...]


class BestXiAssignmentService:
    """Choose the strongest whole XI rather than greedily filling slots in order."""

    def assignmentBuild(
        self,
        requiredSlots: Iterable[object],
        roles: Iterable[object],
    ) -> BestXiAssignment:
        """Optimise coverage, total fit, weakest fit, then stable identity.

        Candidate eligibility is established before optimisation: a player must
        have captured familiarity with the tactic slot's position family.  Generic
        Role Fit alone is deliberately not evidence that the player can reasonably
        be fielded there now.

        Objective priority is deliberately lexicographic:

        1. maximise covered simultaneous tactic slots;
        2. maximise summed slot Generic Role Fit;
        3. maximise the weakest selected slot fit;
        4. use deterministic alphabetical assignment as the final tie-break.

        One player can be assigned to at most one simultaneous slot.
        """

        slots = tuple(requiredSlots)
        roleCatalogue = tuple(roles)
        slotCandidates = tuple(self._slotCandidates(slot, roleCatalogue) for slot in slots)
        evidenceAvailable = any(slotCandidates)
        playerNames = sorted(
            {candidate.playerName for candidates in slotCandidates for candidate in candidates},
            key=str.casefold,
        )
        byPlayerSlot = {
            (candidate.playerName.casefold(), slotIndex): candidate
            for slotIndex, candidates in enumerate(slotCandidates)
            for candidate in candidates
        }

        slotCount = len(slots)
        emptyAssignments: tuple[str | None, ...] = (None,) * slotCount
        emptyScores: tuple[float | None, ...] = (None,) * slotCount
        states: dict[int, _State] = {0: _State(0.0, inf, emptyAssignments, emptyScores)}

        for playerName in playerNames:
            playerKey = playerName.casefold()
            nextStates = dict(states)
            for mask, state in states.items():
                for slotIndex in range(slotCount):
                    if mask & (1 << slotIndex):
                        continue
                    candidate = byPlayerSlot.get((playerKey, slotIndex))
                    if candidate is None:
                        continue
                    assignments = list(state.assignments)
                    scores = list(state.scores)
                    assignments[slotIndex] = candidate.playerName
                    scores[slotIndex] = candidate.score
                    proposed = _State(
                        totalScore=round(state.totalScore + candidate.score, 6),
                        weakestScore=min(state.weakestScore, candidate.score),
                        assignments=tuple(assignments),
                        scores=tuple(scores),
                    )
                    nextMask = mask | (1 << slotIndex)
                    if self._stateBetter(proposed, nextStates.get(nextMask)):
                        nextStates[nextMask] = proposed
            states = nextStates

        bestMask, bestState = 0, states[0]
        for mask, state in states.items():
            if mask.bit_count() > bestMask.bit_count():
                bestMask, bestState = mask, state
                continue
            if mask.bit_count() == bestMask.bit_count() and self._stateBetter(state, bestState):
                bestMask, bestState = mask, state

        covered = bestMask.bit_count()
        weakest = None if covered == 0 else bestState.weakestScore
        assignmentByName = {
            name.casefold(): index
            for index, name in enumerate(bestState.assignments)
            if name is not None
        }
        selections = []
        for slotIndex, playerName in enumerate(bestState.assignments):
            if playerName is None:
                continue
            candidate = byPlayerSlot[(playerName.casefold(), slotIndex)]
            explanation = self._selectionEvidence(
                slotIndex,
                candidate,
                slotCandidates[slotIndex],
                assignmentByName,
                covered,
                slotCount,
                bestState.totalScore,
                weakest,
            )
            selections.append(
                BestXiSelection(
                    slotIndex=slotIndex,
                    playerName=playerName,
                    score=candidate.score,
                    familiar=candidate.familiar,
                    evidence=explanation,
                )
            )

        return BestXiAssignment(
            selections=tuple(selections),
            coveredSlots=covered,
            requiredSlots=slotCount,
            totalScore=round(bestState.totalScore, 1),
            weakestScore=round(weakest, 1) if weakest is not None else None,
            evidenceAvailable=evidenceAvailable,
        )

    def _slotCandidates(
        self,
        slot: object,
        roles: tuple[object, ...],
    ) -> tuple[BestXiSlotCandidate, ...]:
        requirements = []
        for phase, labelAttribute, codeAttribute in (
            ("IP", "ipRole", "ipRoleCode"),
            ("OOP", "oopRole", "oopRoleCode"),
        ):
            label = str(getattr(slot, labelAttribute, "") or "").strip()
            roleCode = str(getattr(slot, codeAttribute, "") or "").strip()
            role = self._roleResolveByCode(roleCode, phase, roles) if roleCode else None
            if role is None:
                # A slot is indivisible evidence: never optimise from the phase
                # that happened to resolve while silently dropping the other.
                return ()
            requirements.append((phase, label or roleCode, role))
        if len(requirements) != 2:
            return ()

        candidateMaps = []
        for _phase, _label, role in requirements:
            candidateMaps.append(
                {
                    str(candidate.name).casefold(): candidate
                    for candidate in getattr(role, "candidates", ())
                    if bool(getattr(candidate, "available", False))
                    and self._scoreParse(getattr(candidate, "score", None)) is not None
                }
            )
        if not candidateMaps:
            return ()

        playerKeys = sorted(set.intersection(*(set(mapping) for mapping in candidateMaps)))
        requiredFamily = positionFamilyFor(str(getattr(slot, "position", "") or ""))
        results = []
        for playerKey in playerKeys:
            scores = []
            evidence = []
            playerName = ""
            capturedPositions = ""
            for (phase, label, _role), candidateMap in zip(requirements, candidateMaps):
                candidate = candidateMap[playerKey]
                playerName = str(candidate.name)
                capturedPositions = capturedPositions or str(
                    getattr(candidate, "positions", "") or ""
                )
                score = self._scoreParse(getattr(candidate, "score", None))
                if score is None:
                    scores = []
                    break
                scores.append(score)
                evidence.append(f"{phase} {label} {score:.1f}")
            if not scores:
                continue
            slotScore = round(sum(scores) / len(scores), 1)
            capturedFamilies = playerPositionFamilies(capturedPositions)
            familiar = requiredFamily is not None and requiredFamily in capturedFamilies
            # Best XI is a current deployability judgement, so position-family
            # evidence has authority over an otherwise strong Generic Role Fit.
            # Unfamiliar candidates remain available to role-depth and future
            # retraining-opportunity analysis; only Best XI excludes them.
            if not familiar:
                continue
            results.append(
                BestXiSlotCandidate(
                    playerName=playerName,
                    score=slotScore,
                    familiar=familiar,
                    evidence=tuple(evidence),
                )
            )
        return tuple(
            sorted(
                results,
                key=lambda candidate: (
                    -candidate.score,
                    candidate.playerName.casefold(),
                ),
            )
        )

    @staticmethod
    def _scoreParse(value: object) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _phaseMatches(role: object, phase: str) -> bool:
        phases = {
            value.strip().casefold()
            for value in str(getattr(role, "phases", "") or "").split(",")
            if value.strip()
        }
        expected = (
            {"ip", "in possession"}
            if phase == "IP"
            else {"oop", "out of possession", "out possession"}
        )
        return not phases or bool(phases & expected)

    @classmethod
    def _roleResolve(
        cls,
        label: str,
        phase: str,
        roles: tuple[object, ...],
    ) -> object | None:
        folded = label.casefold()
        matches = [
            role
            for role in roles
            if cls._isAssignableRole(role)
            and cls._phaseMatches(role, phase)
            and folded
            in {
                str(getattr(role, "abbreviation", "") or "").casefold(),
                str(getattr(role, "displayName", "") or "").casefold(),
                str(getattr(role, "roleCode", "") or "").casefold(),
            }
        ]
        if len(matches) != 1:
            return None
        return matches[0]

    @classmethod
    def _roleResolveByCode(
        cls,
        roleCode: str,
        phase: str,
        roles: tuple[object, ...],
    ) -> object | None:
        """Resolve one tactic slot by durable roleCode, ignoring unresolved placeholders."""

        folded = roleCode.casefold()
        matches = [
            role
            for role in roles
            if cls._isAssignableRole(role)
            and cls._phaseMatches(role, phase)
            and str(getattr(role, "roleCode", "") or "").casefold() == folded
        ]
        if len(matches) != 1:
            return None
        return matches[0]

    @staticmethod
    def _isAssignableRole(role: object) -> bool:
        """Exclude unresolved placeholder rows that only exist for Role Editor workflow."""

        state = str(getattr(role, "resolutionState", "ready") or "ready").casefold()
        return state not in {"unknownrole", "unknown_role"}

    @staticmethod
    def _stateBetter(proposed: _State, existing: _State | None) -> bool:
        if existing is None:
            return True
        proposedObjective = (
            proposed.totalScore,
            proposed.weakestScore,
        )
        existingObjective = (
            existing.totalScore,
            existing.weakestScore,
        )
        if proposedObjective != existingObjective:
            return proposedObjective > existingObjective
        proposedKey = tuple((value or "\uffff").casefold() for value in proposed.assignments)
        existingKey = tuple((value or "\uffff").casefold() for value in existing.assignments)
        return proposedKey < existingKey

    @staticmethod
    def _selectionEvidence(
        slotIndex: int,
        selected: BestXiSlotCandidate,
        candidates: tuple[BestXiSlotCandidate, ...],
        assignmentByName: dict[str, int],
        covered: int,
        required: int,
        totalScore: float,
        weakestScore: float | None,
    ) -> str:
        weakestText = "Unavailable" if weakestScore is None else f"{weakestScore:.1f}"
        parts = [
            f"Global Best XI covers {covered}/{required} simultaneous slots; "
            f"total slot fit {totalScore:.1f}; weakest selected slot {weakestText}.",
            f"Selected slot fit {selected.score:.1f} from {'; '.join(selected.evidence)}.",
        ]
        if candidates:
            localBest = candidates[0]
            if (
                localBest.playerName.casefold() != selected.playerName.casefold()
                and localBest.score > selected.score
            ):
                otherSlot = assignmentByName.get(localBest.playerName.casefold())
                if otherSlot is not None:
                    parts.append(
                        f"{localBest.playerName} scores higher locally at {localBest.score:.1f} "
                        f"but is assigned to slot {otherSlot + 1}; using {selected.playerName} "
                        "here produces the stronger global XI."
                    )
                else:
                    parts.append(
                        f"{localBest.playerName} scores higher locally at {localBest.score:.1f}, "
                        "but the whole-XI objective favours this assignment."
                    )
        parts.append("Captured positional evidence covers this slot family.")
        return " ".join(parts)
