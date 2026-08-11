from __future__ import annotations

from dataclasses import dataclass, field

from .attribute import Attribute
from .instruction import InstructionSet
from .trait import Trait


@dataclass(slots=True)
class RoleProfile:
    """One profile of a football role."""

    name: str
    description: str = ""

    keyAttributes: list[Attribute] = field(default_factory=list)
    keyTraits: list[Trait] = field(default_factory=list)

    instructions: InstructionSet = field(default_factory=dict)