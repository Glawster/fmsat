"""Football Manager instructions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InstructionValue:
    """One possible value for an instruction."""

    name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class Instruction:
    """A Football Manager instruction."""

    name: str
    description: str = ""
    values: tuple[InstructionValue, ...] = ()


InstructionSet = dict[Instruction, InstructionValue]