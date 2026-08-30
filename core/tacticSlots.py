"""Simultaneous IP/OOP tactic-slot pairing from durable ids or spatial evidence.

This module links *positions*. It does not resolve ``roleCode``, score players,
or read squad data. Role Depth and Tactic Analysis consume the same pairing and
apply their own adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import dist

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
    """One simultaneous tactic slot, or one unlinked phase position."""

    slotId: str
    ipPosition: object | None
    oopPosition: object | None
    unavailableReason: str | None


def slotsLink(tactic: object) -> tuple[LinkedTacticSlot, ...]:
    """Pair IP/OOP positions by durable id, correcting clear mirrored crossings."""

    phases = _phasePositions(tactic)
    if not phases:
        return ()

    uniqueByPhase, idsByPhase = _uniqueSlotMaps(phases)
    durableIds = set.intersection(*(set(mapping) for mapping in uniqueByPhase.values()))
    if durableIds:
        return _durableSlotsBuild(phases, uniqueByPhase, idsByPhase, durableIds)

    spatial = _spatialPhaseLink(phases)
    if spatial is not None:
        return spatial
    return _unlinkedSlotsBuild(phases, _LINKAGE_UNAVAILABLE)


def slotSortKey(slot: LinkedTacticSlot) -> tuple[int, int, str, str]:
    position = _canonicalPositionCode(slot)
    line, side = _positionLineSide(position)
    return line, side, position.casefold(), slot.slotId.casefold()


def _phasePositions(tactic: object) -> tuple[tuple[str, tuple[object, ...]], ...]:
    populated: list[tuple[str, tuple[object, ...]]] = []
    for phase, attribute in (("IP", "inPossession"), ("OOP", "outOfPossession")):
        formation = getattr(tactic, attribute, None)
        positions = tuple(getattr(formation, "positions", ()) or ())
        if positions:
            populated.append((phase, positions))
    return tuple(populated)


def _slotId(position: object) -> str:
    return str(getattr(position, "slotId", "") or "")


def _positionCode(position: object | None) -> str:
    if position is None:
        return ""
    canonical = getattr(position, "canonicalPosition", None)
    if canonical:
        return str(canonical)
    identity = getattr(position, "identity", None)
    value = getattr(identity, "value", None)
    return str(value or "")


def _positionGroup(position: object | None) -> str:
    """Return a conservative positional line used only to repair mirrored crossings."""

    code = _positionCode(position).upper().replace(" ", "")
    if code.startswith("DM"):
        return "DM"
    if code.startswith("AM"):
        return "AM"
    if code.startswith("WB"):
        return "WB"
    if code.startswith("ST"):
        return "ST"
    if code.startswith("M"):
        return "M"
    if code.startswith("D"):
        return "D"
    if code == "GK":
        return "GK"
    return code


def _uniqueSlotMaps(
    phases: tuple[tuple[str, tuple[object, ...]], ...],
) -> tuple[dict[str, dict[str, object]], dict[str, tuple[str, ...]]]:
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
    referencePhase, _positions = max(phases, key=lambda item: len(item[1]))
    referenceIds = tuple(slotId for slotId in idsByPhase[referencePhase] if slotId in durableIds)
    linked = tuple(_linkedFromUnique(slotId, uniqueByPhase) for slotId in referenceIds)
    linked = _repairMirroredCanonicalCrossings(linked)

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


def _repairMirroredCanonicalCrossings(
    linked: tuple[LinkedTacticSlot, ...],
) -> tuple[LinkedTacticSlot, ...]:
    """Repair crossed L/R durable ids when canonical positions prove the pairing.

    A regenerated model can preserve unique slotIds while accidentally swapping
    two mirrored positions between phases. When a positional line has the same
    unique canonical position set in IP and OOP, exact canonical identity is
    stronger evidence than the crossed imported ids for that line only.
    Genuine family changes such as AMR -> MR are untouched because the position
    sets for that line do not match.
    """

    result = list(linked)
    groups = sorted({_positionGroup(slot.ipPosition) for slot in linked if slot.ipPosition})
    for group in groups:
        indexes = [
            index
            for index, slot in enumerate(result)
            if _positionGroup(slot.ipPosition) == group
            and _positionGroup(slot.oopPosition) == group
            and slot.ipPosition is not None
            and slot.oopPosition is not None
        ]
        if len(indexes) < 2:
            continue

        ipCodes = [_positionCode(result[index].ipPosition) for index in indexes]
        oopCodes = [_positionCode(result[index].oopPosition) for index in indexes]
        if not all(ipCodes) or not all(oopCodes):
            continue
        if len(set(ipCodes)) != len(ipCodes) or len(set(oopCodes)) != len(oopCodes):
            continue
        if set(ipCodes) != set(oopCodes):
            continue
        if all(ip == oop for ip, oop in zip(ipCodes, oopCodes)):
            continue

        oopByCode = {_positionCode(result[index].oopPosition): result[index].oopPosition for index in indexes}
        for index in indexes:
            slot = result[index]
            ipCode = _positionCode(slot.ipPosition)
            result[index] = LinkedTacticSlot(
                slotId=slot.slotId,
                ipPosition=slot.ipPosition,
                oopPosition=oopByCode[ipCode],
                unavailableReason=slot.unavailableReason,
            )
    return tuple(result)


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
    return _positionCode(position)


def _positionLineSide(position: str) -> tuple[int, int]:
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
