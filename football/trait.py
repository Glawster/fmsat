from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Trait:
    """A Football Manager player trait."""

    name: str
    description: str = ""