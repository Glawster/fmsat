from __future__ import annotations

from dataclasses import dataclass, field

from fmsat.football.instruction import InstructionSet
from fmsat.football.role import Role
from fmsat.football.roleProfile import RoleProfile

from .positionIdentity import PositionIdentity


@dataclass(slots=True)
class Position:
    """One position within a formation."""

    identity: PositionIdentity
    role: Role
    roleProfile: RoleProfile

    instructions: InstructionSet = field(default_factory=dict)

    needs: list = field(default_factory=list)