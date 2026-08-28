"""Simultaneous IP/OOP tactic-slot pairing from durable ids or spatial evidence.

This module links *positions*. It does not resolve ``roleCode``, score players,
or read squad data. Role Depth and Tactic Analysis consume the same pairing and
apply their own adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import dist

# Spatial recovery is a last resort when every phase is missing a complete
# unique slotId intersection. Distances are in the normalised pitch coordinates
# stored on the object model (0..1). The margin rejects two equally plausible
# complete mappings rather than inventing an ordinal partner.
_SPATIAL_MAX_DISTANCE = 0.38
_SPATIAL_AMBIGUITY_MARGIN = 0.05

_LINKAGE_UNAVAILABLE = (
    "Tactic slot linkage is unavailable; complete matching slotId or "
    "unambiguous spatial evidence is required"
)
_LINKAGE_UNAVAILABLE_POSITION = (
    "Tactic slot linkage is unavailable for this position; a matching "
    "durable slotId in every phase is required"
)


@dataclass(frozen=True, slots=True)
class LinkedTacticSlot:
    """One simultaneous tactic slot, or one unlinked phase position.

    A successful link has ``unavailableReason is None``. A missing phase on a
    successful one-phase tactic is represented as ``None`` on that side without
    a linkage failure. Failed pairing never invents an IP/OOP partner: each
    leftover position is its own unlinked slot.
    """

    slotId: str
    ipPosition: object | None
    oopPosition: object | None
    unavailableReason: str | None


def slotsLink(tactic: object) -> tuple[LinkedTacticSlot, ...]:
    """Pair IP/OOP positions by unique ``slotId``, else by unique spatial match.

    Do not pair by list order. Do not consult an assigned footballer, duty,
    or any squad model.
    """

    phases = _phasePositions(tactic)
    if not phases:
        return ()

    uniqueByPhase, idsByPhase = _uniqueSlotMaps(phases)
    durableIds = set.intersection(*(set(mapping) for mapping in uniqueByPhase.values()))
    if durableIds:
        return _durableSlotsBuild(phases, uniqueByPhase, idsByPhase, durableIds)

    # No shared unique id exists in every populated phase. Spatial recovery is
    # all-or-nothing: a single ambiguous pair makes the whole mapping Unavailable.
    spatial = _spatialPhaseLink(phases)
    if spatial is not None:
        return spatial
    return _unlinkedSlotsBuild(phases, _LINKAGE_UNAVAILABLE)


def slotSortKey(slot: LinkedTacticSlot) -> tuple[int, int, str, str]:
    """Order slots from forwards back to goalkeeper using one canonical position.

    The position is IP when present, otherwise OOP. Display strings such as
    ``AML → ML`` are not a sort key. Codes that share a line and side, such as
    ``AML`` and ``AMCL``, then sort by the compact code and ``slotId``.
    """

    position = _canonicalPositionCode(slot)
    line, side = _positionLineSide(position)
    return line, side, position.casefold(), slot.slotId.casefold()


def _phasePositions(tactic: object) -> tuple[tuple[str, tuple[object, ...]], ...]:
    """Return populated phases in IP then OOP order."""

    populated: list[tuple[str, tuple[object, ...]]] = []
    for phase, attribute in (("IP", "inPossession"), ("OOP", "outOfPossession")):
        formation = getattr(tactic, attribute, None)
        positions = tuple(getattr(formation, "positions", ()) or ())
        if positions:
            populated.append((phase, positions))
    return tuple(populated)


def _slotId(position: object) -> str:
    return str(getattr(position, "slotId", "") or "")


def _uniqueSlotMaps(
    phases: tuple[tuple[str, tuple[object, ...]], ...],
) -> tuple[dict[str, dict[str, object]], dict[str, tuple[str, ...]]]:
    """Keep a slotId only when it appears once in that phase.

    Duplicate ids are evidence of a broken import, not a pairing key.
    """

    uniqueByPhase: dict[str, dict[str, object]] = {}
    idsByPhase: dict[str, tuple[str, ...]] = {}
    for phase, positions in phases:
        ids = tuple(_slotId(position) for position in positions)
        idsByPhase[phase] = ids
        counts = {slotId: ids.count(slotId) for slotId in set(ids) if slotId}
        uniqueByPhase[phase] = {
            slotId: position
            for slotId, position in zip(ids, positions)
            if slotId and counts[slotId] == 1
        }
    return uniqueByPhase, idsByPhase


def _durableSlotsBuild(
    phases: tuple[tuple[str, tuple[object, ...]], ...],
    uniqueByPhase: dict[str, dict[str, object]],
    idsByPhase: dict[str, tuple[str, ...]],
    durableIds: set[str],
) -> tuple[LinkedTacticSlot, ...]:
    """Emit complete durable pairs first, then each leftover as unlinked."""

    referencePhase, _positions = max(phases, key=lambda item: len(item[1]))
    referenceIds = tuple(slotId for slotId in idsByPhase[referencePhase] if slotId in durableIds)
    linked = tuple(_linkedFromUnique(slotId, uniqueByPhase) for slotId in referenceIds)

    leftovers: list[LinkedTacticSlot] = []
    for phase, positions in phases:
        for index, position in enumerate(positions):
            if _slotId(position) in durableIds:
                continue
            leftovers.append(
                _unlinkedSlot(
                    index=len(leftovers),
                    phase=phase,
                    position=position,
                    reason=_LINKAGE_UNAVAILABLE_POSITION,
                )
            )
    return linked + tuple(leftovers)


def _linkedFromUnique(slotId: str, uniqueByPhase: dict[str, dict[str, object]]) -> LinkedTacticSlot:
    return LinkedTacticSlot(
        slotId=slotId,
        ipPosition=uniqueByPhase.get("IP", {}).get(slotId),
        oopPosition=uniqueByPhase.get("OOP", {}).get(slotId),
        unavailableReason=None,
    )


def _unlinkedSlotsBuild(
    phases: tuple[tuple[str, tuple[object, ...]], ...],
    reason: str,
) -> tuple[LinkedTacticSlot, ...]:
    """Retain every observed position without inventing a cross-phase partner."""

    slots: list[LinkedTacticSlot] = []
    for phase, positions in phases:
        for position in positions:
            slots.append(
                _unlinkedSlot(index=len(slots), phase=phase, position=position, reason=reason)
            )
    return tuple(slots)


def _unlinkedSlot(*, index: int, phase: str, position: object, reason: str) -> LinkedTacticSlot:
    return LinkedTacticSlot(
        slotId=f"unlinked:{index + 1}",
        ipPosition=position if phase == "IP" else None,
        oopPosition=position if phase == "OOP" else None,
        unavailableReason=reason,
    )


def _spatialPhaseLink(
    phases: tuple[tuple[str, tuple[object, ...]], ...],
) -> tuple[LinkedTacticSlot, ...] | None:
    """Recover complete phase linkage only when the global spatial match is unique."""

    if len(phases) != 2:
        return None
    firstPhase, firstPositions = phases[0]
    secondPhase, secondPositions = phases[1]
    if len(firstPositions) != len(secondPositions) or not firstPositions:
        return None
    if any(
        getattr(position, "x", None) is None or getattr(position, "y", None) is None
        for _phase, positions in phases
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
    if max(pairDistances, default=0.0) > _SPATIAL_MAX_DISTANCE:
        return None
    if secondCost is not None and secondCost - bestCost < _SPATIAL_AMBIGUITY_MARGIN:
        return None

    # Label recovered links independently of either phase's stored slotId so a
    # mismatched import identity cannot look like a durable match.
    slotIds = tuple(f"spatial:{index + 1:02d}" for index in range(count))
    slots: list[LinkedTacticSlot] = []
    for index, slotId in enumerate(slotIds):
        firstPosition = source[index]
        secondPosition = target[bestAssignment[index]]
        slots.append(
            LinkedTacticSlot(
                slotId=slotId,
                ipPosition=firstPosition if firstPhase == "IP" else secondPosition,
                oopPosition=secondPosition if secondPhase == "OOP" else firstPosition,
                unavailableReason=None,
            )
        )
    return tuple(slots)


def _canonicalPositionCode(slot: LinkedTacticSlot) -> str:
    position = slot.ipPosition if slot.ipPosition is not None else slot.oopPosition
    if position is None:
        return ""
    canonical = getattr(position, "canonicalPosition", None)
    if canonical:
        return str(canonical)
    identity = getattr(position, "identity", None)
    value = getattr(identity, "value", None)
    return str(value or "")


def _positionLineSide(position: str) -> tuple[int, int]:
    """Match ``app.presentation.positionSortKey`` without importing the UI."""

    compact = position.upper().replace(" ", "").replace("(", "").replace(")", "")
    if compact.startswith("ST"):
        line = 0
    elif compact.startswith("AM"):
        line = 1
    elif compact.startswith("M") and not compact.startswith("AM"):
        line = 2
    elif compact.startswith("DM"):
        line = 3
    elif compact.startswith("WB") or (compact.startswith("D") and not compact.startswith("DM")):
        line = 4
    elif compact == "GK":
        line = 5
    else:
        line = 6
    side = (
        0
        if compact.endswith("L")
        else 1 if compact.endswith("C") else 2 if compact.endswith("R") else 3
    )
    return line, side
