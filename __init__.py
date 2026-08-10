"""Reverse engineering toolkit for Football Manager tactic files."""

from fmsat.core.logUtils import getApplication, setApplication

try:
    getApplication()
except RuntimeError:
    setApplication("fmsat")

from fmsat.fmf.parser import FMFParser, FMFTactic
from fmsat.fmf.structures import FileInspection, TacticMetadata

__all__ = ["FMFTactic", "FMFParser", "FileInspection", "TacticMetadata"]
