"""Reverse engineering toolkit for Football Manager tactic files."""

from fmsat.core.logUtils import getApplication, setApplication

try:
    getApplication()
except RuntimeError:
    setApplication("fmsat")

from fmsat.fmf.parser import FMFParser, FMFTactic
from fmsat.fmf.structures import FileInspection, TacticMetadata

import importlib

try:
    cli = importlib.import_module("fmsat.cli")
except Exception:  # pragma: no cover - import-time compatibility fallback
    cli = None

__all__ = ["FMFTactic", "FMFParser", "FileInspection", "TacticMetadata", "cli"]
