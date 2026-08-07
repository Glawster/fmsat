"""Football Manager role-profile screenshot evidence."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RoleProfileEvidence:
    """Facts observed on one Football Manager role-profile screen.

    ``keyAttributes`` records which attributes Football Manager identifies as
    important to the role. ``displayedPlayerAttributes`` contains the selected
    player's visible ratings; those ratings are evidence about the player and
    must never be interpreted as role weights.
    """

    position: str
    roleName: str
    abbreviation: str | None = None
    behaviours: tuple[str, ...] = ()
    description: str | None = None
    keyAttributes: tuple[str, ...] = ()
    playerInstructions: tuple[str, ...] = ()
    displayedPlayerAttributes: dict[str, int] = field(default_factory=dict)
    suitabilityStars: float | None = None
    sourceImport: str | None = None

    def __post_init__(self) -> None:
        """Reject impossible displayed values without inventing missing data."""

        invalidAttributes = {
            name: value
            for name, value in self.displayedPlayerAttributes.items()
            if value < 1 or value > 20
        }
        if invalidAttributes:
            raise ValueError(
                "Displayed Football Manager attributes must be between 1 and 20: "
                f"{invalidAttributes}"
            )
        if self.suitabilityStars is not None and not 0 <= self.suitabilityStars <= 5:
            raise ValueError("Displayed role suitability must be between 0 and 5 stars")

    def playerValuesForKeyAttributes(self) -> dict[str, int]:
        """Return visible player ratings limited to the role's key attributes."""

        return {
            attribute: self.displayedPlayerAttributes[attribute]
            for attribute in self.keyAttributes
            if attribute in self.displayedPlayerAttributes
        }
