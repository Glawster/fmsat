"""String mapping for Tactic Analysis. The view must not calculate demand."""

from __future__ import annotations

from dataclasses import dataclass

from fmsat.core.tacticAnalysis import (
    AttributeDemand,
    TacticAnalysis,
    TacticObservation,
    TacticPhaseRole,
    TacticSlotDemand,
)


@dataclass(frozen=True, slots=True)
class TacticSlotDisplay:
    """One Role Requirements row."""

    position: str
    ipRole: str
    oopRole: str
    transition: str
    evidence: str
    positionToolTip: str
    ipToolTip: str
    oopToolTip: str
    evidenceToolTip: str


@dataclass(frozen=True, slots=True)
class TacticDemandDisplay:
    """One Attribute Demand row. None from core becomes Unavailable."""

    attribute: str
    inPossession: str
    outOfPossession: str
    contributors: str
    toolTip: str


@dataclass(frozen=True, slots=True)
class TacticObservationDisplay:
    """One structural observation row."""

    phase: str
    finding: str
    evidence: str


@dataclass(frozen=True, slots=True)
class TacticAnalysisDisplay:
    """UI-ready strings for the Tactic Analysis dashboard."""

    banner: str
    slots: tuple[TacticSlotDisplay, ...]
    demand: tuple[TacticDemandDisplay, ...]
    observations: tuple[TacticObservationDisplay, ...]


def tacticAnalysisDisplayBuild(analysis: TacticAnalysis) -> TacticAnalysisDisplay:
    """Adapt core demand results into table strings without recalculating them."""

    coverage = f"{analysis.weightCompletePhaseRoles}/{analysis.weightExpectedPhaseRoles}"
    banner = f"Policy: {analysis.scoringIdentity} · {coverage} phase-roles ready"
    if analysis.demandCoverageReason:
        banner = f"{banner}\n{analysis.demandCoverageReason}"
    return TacticAnalysisDisplay(
        banner=banner,
        slots=tuple(_slotDisplay(slot) for slot in analysis.slots),
        demand=tuple(_demandDisplay(row) for row in analysis.overallDemand),
        observations=tuple(_observationDisplay(item) for item in analysis.observations),
    )


def _slotDisplay(slot: TacticSlotDemand) -> TacticSlotDisplay:
    ip = slot.ipRole.canonicalPosition
    oop = slot.oopRole.canonicalPosition
    if ip and oop and ip != oop:
        position = f"{ip} → {oop}"
    else:
        position = ip or oop or "Unavailable"
    return TacticSlotDisplay(
        position=position,
        ipRole=_roleLabel(slot.ipRole),
        oopRole=_roleLabel(slot.oopRole),
        transition=slot.transition.explanation or "Unavailable",
        evidence=_evidenceLabel(slot),
        positionToolTip=slot.slotId,
        ipToolTip=_roleToolTip(slot.ipRole),
        oopToolTip=_roleToolTip(slot.oopRole),
        evidenceToolTip=_evidenceToolTip(slot),
    )


def _roleLabel(role: TacticPhaseRole) -> str:
    if role.resolutionState == "missingPhase":
        return "—"
    return role.abbreviation or role.displayName or "Unavailable"


def _roleToolTip(role: TacticPhaseRole) -> str:
    parts = [part for part in (role.roleCode, role.unavailableReason) if part]
    return "\n".join(parts)


def _evidenceLabel(slot: TacticSlotDemand) -> str:
    if slot.linkageUnavailableReason:
        return "Unlinked"
    states = {slot.ipRole.resolutionState, slot.oopRole.resolutionState}
    if "unresolved" in states:
        return "Unresolved role"
    if "recognitionOnly" in states:
        return "Recognition only"
    if "missingWeights" in states:
        return "Missing weights"
    if "ready" in states and "missingPhase" in states:
        return "Partial"
    if "ready" in states:
        return "Ready"
    return "Unavailable"


def _evidenceToolTip(slot: TacticSlotDemand) -> str:
    parts = [
        part
        for part in (
            slot.linkageUnavailableReason,
            slot.ipRole.unavailableReason,
            slot.oopRole.unavailableReason,
        )
        if part
    ]
    return "\n".join(parts)


def _demandDisplay(row: AttributeDemand) -> TacticDemandDisplay:
    noun = "phase-role" if row.contributingPhaseRoles == 1 else "phase-roles"
    return TacticDemandDisplay(
        attribute=row.displayName,
        inPossession=_number(row.inPossession),
        outOfPossession=_number(row.outOfPossession),
        contributors=str(row.contributingPhaseRoles),
        toolTip=(
            f"{row.contributingPhaseRoles} contributing {noun}. "
            "Excluded roles do not contribute 0."
        ),
    )


def _observationDisplay(item: TacticObservation) -> TacticObservationDisplay:
    return TacticObservationDisplay(
        phase=item.phase or "—",
        finding=item.title,
        evidence=item.explanation,
    )


def _number(value: int | None) -> str:
    return "Unavailable" if value is None else str(value)
