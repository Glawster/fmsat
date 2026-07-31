"""Validation of OCR-derived player records."""

from __future__ import annotations

from dataclasses import dataclass

from ..parser import ExtractedPlayer


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One actionable validation problem."""

    field: str
    message: str


class PlayerValidator:
    """Checks required fields, confidence, and Football Manager attribute ranges."""

    def __init__(self, confidenceThreshold: float = 0.95) -> None:
        self.confidenceThreshold = confidenceThreshold

    def isLowConfidence(self, player: ExtractedPlayer) -> bool:
        """Return whether a row should be highlighted for review."""

        return player.confidence < self.confidenceThreshold

    def validate(self, player: ExtractedPlayer) -> list[ValidationIssue]:
        """Return all issues rather than failing on the first OCR problem."""

        issues: list[ValidationIssue] = []
        if not player.name.strip():
            issues.append(ValidationIssue("name", "Player name is required"))
        if self.isLowConfidence(player):
            issues.append(
                ValidationIssue(
                    "confidence",
                    f"Confidence is below {self.confidenceThreshold:.0%}",
                )
            )
        for name, value in player.attributes.items():
            if value is not None and not 1 <= value <= 20:
                issues.append(ValidationIssue(name, "Attribute must be between 1 and 20"))
        return issues
