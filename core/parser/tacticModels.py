"""Framework-independent structured tactic data."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TacticalPhase(StrEnum):
    """A screen or shape represented by structured tactic data."""

    FORMATION = "formation"
    IN_POSSESSION = "inPossession"
    OUT_OF_POSSESSION = "outOfPossession"


class ValidationState(StrEnum):
    """Review state for an extracted tactical value."""

    EXTRACTED = "extracted"
    CORRECTED = "corrected"
    CONFIRMED = "confirmed"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class TacticIssue:
    """A parser or validation finding requiring review."""

    code: str
    message: str
    observedText: str | None = None


@dataclass(frozen=True, slots=True)
class FormationSlot:
    """One visible tactical slot in one phase."""

    slotId: str
    phase: TacticalPhase
    position: str | None
    role: str | None
    duty: str | None
    x: float
    y: float
    observedRole: str = ""
    displayedPlayer: str | None = None
    confidence: float = 0.0
    sourceImport: str | None = None
    validationState: ValidationState = ValidationState.EXTRACTED


@dataclass(frozen=True, slots=True)
class TeamInstruction:
    """One explicit team instruction extracted from a phase screen."""

    phase: TacticalPhase
    category: str
    value: str | bool | None
    displayValue: str
    confidence: float
    sourceImport: str | None = None
    validationState: ValidationState = ValidationState.EXTRACTED


@dataclass(frozen=True, slots=True)
class StructuredTactic:
    """The current typed representation assembled from tactic screenshots."""

    name: str
    slots: tuple[FormationSlot, ...] = ()
    instructions: tuple[TeamInstruction, ...] = ()
    issues: tuple[TacticIssue, ...] = ()
    confirmed: bool = False
    complete: bool = False
    metadata: dict[str, str] = field(default_factory=dict)
