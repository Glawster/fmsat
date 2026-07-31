"""Framework-independent extracted player data."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ExtractedPlayer:
    """An editable player row produced from one screenshot."""

    name: str
    positions: str
    ca: str
    pa: str
    attributes: dict[str, int | None] = field(default_factory=dict)
    confidence: float = 0.0
