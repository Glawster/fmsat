from __future__ import annotations

from dataclasses import dataclass

from .roleIdentity import RoleIdentity


@dataclass(slots=True)
class Role:
    """A reusable Football Manager role."""

    identity: RoleIdentity
    description: str = ""