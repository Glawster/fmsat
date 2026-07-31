"""Configuration-driven screenshot requirements for a tactic import."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .detection import ScreenType


@dataclass(frozen=True, slots=True)
class ScreenshotRequirement:
    """One screenshot the user may need to capture."""

    screenType: ScreenType
    title: str
    instructions: str


@dataclass(frozen=True, slots=True)
class ScreenshotPlan:
    """Completed and outstanding screenshots for a named tactic."""

    tacticName: str
    completed: tuple[ScreenshotRequirement, ...]
    missing: tuple[ScreenshotRequirement, ...]

    @property
    def isComplete(self) -> bool:
        """Return whether every configured screenshot already exists."""

        return not self.missing


class TacticScreenshotPlanner:
    """Compares configured requirements with screenshots already stored locally."""

    def __init__(self, requirements: tuple[ScreenshotRequirement, ...]) -> None:
        if not requirements:
            raise ValueError("At least one screenshot requirement must be configured")
        self.requirements = requirements

    @classmethod
    def fromMapping(cls, values: dict[str, Any]) -> TacticScreenshotPlanner:
        """Build a planner from the workflow section of screens.yaml."""

        requirements = tuple(
            ScreenshotRequirement(
                screenType=ScreenType(str(item["type"])),
                title=str(item["title"]),
                instructions=str(item["instructions"]),
            )
            for item in values.get("required_screens", [])
        )
        return cls(requirements)

    def plan(self, tacticName: str, captured: set[ScreenType]) -> ScreenshotPlan:
        """Return the completed and missing requirements in configured order."""

        completed = tuple(
            requirement for requirement in self.requirements if requirement.screenType in captured
        )
        missing = tuple(
            requirement
            for requirement in self.requirements
            if requirement.screenType not in captured
        )
        return ScreenshotPlan(tacticName.strip(), completed, missing)
