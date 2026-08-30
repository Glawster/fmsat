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
class TacticExplanationDisplay:
    """Deterministic content for the shared Explain this dialog."""

    title: str
    meaning: str
    footballMeaning: str
    calculation: str


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
    explanation: TacticExplanationDisplay


@dataclass(frozen=True, slots=True)
class TacticDemandDisplay:
    """One Attribute Demand row. None from core becomes Unavailable."""

    attribute: str
    inPossession: str
    outOfPossession: str
    contributors: str
    toolTip: str
    explanation: TacticExplanationDisplay


@dataclass(frozen=True, slots=True)
class TacticObservationDisplay:
    """One structural observation row."""

    phase: str
    finding: str
    evidence: str
    explanation: TacticExplanationDisplay


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
        explanation=_slotExplanation(slot, position),
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


def _slotExplanation(slot: TacticSlotDemand, position: str) -> TacticExplanationDisplay:
    ip = slot.ipRole
    oop = slot.oopRole
    if ip.resolutionState == "missingPhase" or oop.resolutionState == "missingPhase":
        football = (
            "Only one possession phase exists for this slot, so FMSAT does not invent "
            "the missing position or a transition."
        )
    elif slot.transition.classification == "familyChange":
        football = (
            f"This tactical position moves from the {slot.transition.ipFamily} position "
            f"family to the {slot.transition.oopFamily} position family when possession changes."
        )
    elif slot.transition.classification == "roleChangeSameFamily":
        football = (
            "The role changes between phases, but the position remains within the same "
            "canonical position family."
        )
    elif slot.transition.classification == "unchanged":
        football = "The linked phases use the same role identity."
    else:
        football = "FMSAT cannot reliably describe a phase transition for this slot."

    meaningParts = []
    if ip.resolutionState != "missingPhase":
        meaningParts.append(
            f"With the ball, this slot is {ip.canonicalPosition} and uses {ip.displayName}."
        )
    if oop.resolutionState != "missingPhase":
        meaningParts.append(
            f"Without the ball, the same simultaneous slot is {oop.canonicalPosition} "
            f"and uses {oop.displayName}."
        )
    calculation = (
        f"FMSAT linked slot {slot.slotId} and compared its resolved role identities and "
        "canonical position families. " + _evidenceExplanation(slot)
    )
    return TacticExplanationDisplay(
        title=f"Role requirement — {position}",
        meaning=" ".join(meaningParts) or "The phase positions for this slot are unavailable.",
        footballMeaning=football,
        calculation=calculation,
    )


def _evidenceExplanation(slot: TacticSlotDemand) -> str:
    if slot.linkageUnavailableReason:
        return (
            "FMSAT could not reliably pair the phase positions, so it does not invent a "
            f"transition. Evidence: {slot.linkageUnavailableReason}."
        )
    states = {slot.ipRole.resolutionState, slot.oopRole.resolutionState}
    if "unresolved" in states:
        return "A stored role could not be resolved to a known roleCode, so it remains unavailable rather than being guessed."
    if "missingWeights" in states:
        return "A role identity is known, but its assessment weights are missing or unusable, so it cannot contribute to Attribute Demand."
    if "recognitionOnly" in states:
        return "FMSAT recognises a role, but currently has no usable assessment weights for it; it is shown here but excluded from Attribute Demand."
    if "ready" in states and "missingPhase" in states:
        return "The present role has usable assessment weights, but its paired phase position does not exist; this slot is therefore Partial."
    if states == {"ready"}:
        return "Both roles are recognised and have usable assessment weights, so they contribute to Attribute Demand."
    return "The available evidence is incomplete, so FMSAT leaves the result unavailable."


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
        explanation=_demandExplanation(row),
    )


def _demandExplanation(row: AttributeDemand) -> TacticExplanationDisplay:
    contributors = "\n".join(
        f"• {item.phase} {item.canonicalPosition} — {item.displayName}: weight {item.weight}"
        for item in row.contributors
    )
    calculation = (
        f"Overall is the sum of the {row.displayName} assessment weights for the ready "
        "role definitions used by the tactic. "
        f"In Possession contributes {_number(row.inPossession)} and Out Of Possession "
        f"contributes {_number(row.outOfPossession)}.\n\nContributing phase-roles:\n{contributors}"
    )
    return TacticExplanationDisplay(
        title=f"{row.displayName} — Overall demand: {_number(row.overall)}",
        meaning=(
            f"{row.contributingPhaseRoles} assessed phase-role"
            f"{'s' if row.contributingPhaseRoles != 1 else ''} contribute to this combined demand."
        ),
        footballMeaning=f"This tactic places a combined role-definition demand on {row.displayName}.",
        calculation=calculation + "\n\nThis is not a player rating, percentage, or 0–100 score.",
    )


def _observationDisplay(item: TacticObservation) -> TacticObservationDisplay:
    return TacticObservationDisplay(
        phase=item.phase or "—",
        finding=item.title,
        evidence=_observationEvidence(item),
        explanation=_observationExplanation(item),
    )


def _observationEvidence(item: TacticObservation) -> str:
    """Keep internal Tracking roleCode values out of the primary table text."""

    if item.code == "trackingRoleCount":
        if not item.positions:
            return "0 tracking phase-roles"
        return f"{item.count} tracking phase-roles: " + ", ".join(item.positions)
    return item.explanation


def _observationExplanation(item: TacticObservation) -> TacticExplanationDisplay:
    if item.code == "repeatedRole":
        meaning = f"{item.roleDisplayName} is used in {item.count} {item.phase} slots."
        football = f"The same role appears at {', '.join(item.positions)} in this phase."
        calculation = f"FMSAT grouped resolved roleCode {item.roleCode} within {item.phase} and counted its canonical positions."
    elif item.code == "asymmetricFlank":
        meaning = "Both left and right positions exist in the same phase but use different roles."
        football = item.explanation
        calculation = f"FMSAT compared the resolved roles at {' and '.join(item.positions)} within {item.phase}."
    elif item.code == "trackingRoleCount":
        meaning = f"{item.count} phase-role assignments use an explicitly defined Tracking role."
        football = (
            "\n".join(item.positions)
            if item.positions
            else "No Tracking role assignments are present."
        )
        calculation = "FMSAT counted resolved roleCode values in its closed set of explicitly defined Tracking roles."
    elif item.code == "familyChangeCount":
        meaning = f"{item.count} of {item.total} classifiable linked slots change position family."
        football = "A position-family change means a linked slot moves between canonical position groups when possession changes."
        calculation = "FMSAT counted linked slots whose IP and OOP canonical position families both resolve, then counted those whose families differ."
    else:
        values = ", ".join(f"{name} {value}" for name, value in item.attributes)
        meaning = f"These are the highest combined attribute demands across the tactic: {values}."
        football = "This does not mean these attributes are automatically the most important for every individual player."
        calculation = (
            "FMSAT ordered the raw combined Attribute Demand totals and selected the first three."
        )
    return TacticExplanationDisplay(item.title, meaning, football, calculation)


def _number(value: int | None) -> str:
    return "Unavailable" if value is None else str(value)
