from __future__ import annotations

from dataclasses import dataclass, field

from .formation import Formation
from .transition import Transition


@dataclass(slots=True)
class Tactic:
    """A complete football tactic."""

    name: str

    inPossession: Formation
    outOfPossession: Formation

    transition: Transition = field(default_factory=Transition)