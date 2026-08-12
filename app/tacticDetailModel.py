"""UI-ready models consumed by the tactic detail workspace."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DisplaySlot:
    """One formation slot using normalized pitch coordinates."""

    slotId: str
    position: str
    role: str
    duty: str
    x: float
    y: float
    row: str
    player: str | None = None


@dataclass(frozen=True, slots=True)
class TacticDetailModel:
    """Display data required to render one tactic detail workspace."""

    formation: str
    mentality: str
    status: str
    assignedSquads: str
    updated: str
    revisions: tuple[str, ...]
    formationSlots: tuple[DisplaySlot, ...]
    outOfPossessionSlots: tuple[DisplaySlot, ...]
    summaryItems: tuple[tuple[str, str], ...]
    notes: str
    instructionGroups: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]
