"""Typed access to FMSAT YAML configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(RuntimeError):
    """Raised when configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class AttributeDefinition:
    """A configurable Football Manager attribute column."""

    name: str
    abbreviation: str
    order: int


class Configuration:
    """Loads application configuration from a replaceable directory."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or Path(__file__).parents[1] / "config"
        self.screens = self._yamlLoad("screens.yaml")
        self.regions = self._yamlLoad("regions.yaml")
        self.tacticExtraction = self._yamlLoad("tacticExtraction.yaml")
        attributeData = self._yamlLoad("attributes.yaml")
        rawAttributes = attributeData.get("attributes", {})
        if not isinstance(rawAttributes, dict):
            raise ConfigurationError("attributes.yaml must contain an attributes mapping")
        self.attributes = tuple(
            sorted(
                (
                    AttributeDefinition(
                        name=name,
                        abbreviation=str(values["abbreviation"]),
                        order=int(values["order"]),
                    )
                    for name, values in rawAttributes.items()
                ),
                key=lambda item: item.order,
            )
        )

    def confidenceThreshold(self) -> float:
        """Return the row confidence threshold as a value between zero and one."""

        return float(self.screens.get("validation", {}).get("confidence_threshold", 0.95))

    def _yamlLoad(self, filename: str) -> dict[str, Any]:
        path = self.directory / filename
        try:
            with path.open(encoding="utf-8") as stream:
                data = yaml.safe_load(stream) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"Unable to load {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigurationError(f"{path} must contain a YAML mapping")
        return data
