from __future__ import annotations

from dataclasses import dataclass, field

from fmsat.football.instruction import InstructionSet

from .position import Position


@dataclass(slots=True)
class Formation:
    """One tactical formation."""

    name: str

    positions: list[Position] = field(default_factory=list)

    instructions: InstructionSet = field(default_factory=dict)