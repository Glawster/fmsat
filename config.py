"""User configuration for FMParser."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def configLoad(configPath: Path | None = None) -> dict[str, Any]:
    """Load user configuration, preserving unknown keys."""

    path = configPath or configPathDefault()
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a JSON object: {path}")
    return data


def configPathDefault() -> Path:
    """Return the default FMParser config path."""

    override = os.environ.get("FMPARSER_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "fmparser" / "config.json"


def configSave(config: dict[str, Any], configPath: Path | None = None) -> Path:
    """Save user configuration as a JSON object."""

    path = configPath or configPathDefault()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def tacticDefaultGet(configPath: Path | None = None) -> Path | None:
    """Return the configured default tactic path when present."""

    value = configLoad(configPath).get("tactic")
    if not isinstance(value, str) or not value:
        return None
    return Path(value).expanduser()


def tacticDefaultSet(tacticPath: Path, configPath: Path | None = None) -> Path:
    """Store the default tactic path and preserve other config values."""

    resolvedPath = tacticPath.expanduser().resolve()
    config = configLoad(configPath)
    config["tactic"] = str(resolvedPath)
    return configSave(config, configPath)
