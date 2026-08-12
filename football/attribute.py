from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Attribute:
    """A Football Manager player attribute."""

    name: str
    weighting: int = 0