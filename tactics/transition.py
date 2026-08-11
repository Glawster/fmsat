from __future__ import annotations

from dataclasses import dataclass, field

from fmsat.football.instruction import InstructionSet


@dataclass(slots=True)
class Transition:
    """How the team reacts when possession changes."""

    instructions: InstructionSet = field(default_factory=dict)