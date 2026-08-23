from __future__ import annotations

from dataclasses import dataclass, field

from fmsat.football.instruction import InstructionSet
from fmsat.football.role import Role
from fmsat.football.roleProfile import RoleProfile

from .positionFamily import PositionFamily, positionFamilyFor
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

    @property
    def family(self) -> PositionFamily | None:
        """Return the role-compatibility family while retaining exact slot geometry."""

        value = self.canonicalPosition or self.identity.value
        return positionFamilyFor(value)
