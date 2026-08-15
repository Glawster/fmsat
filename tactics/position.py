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

    # Evidence retained from the screenshot-derived definition. Identity and
    # role remain the canonical mapped values used by the football model.
    slotId: str | None = None
    duty: str | None = None
    x: float | None = None
    y: float | None = None
    player: str | None = None
    confidence: float | None = None
    sourceImportSessionId: int | None = None
    validationState: str = "unresolved"
    canonicalPosition: str | None = None
    canonicalRole: str | None = None

    needs: list = field(default_factory=list)
