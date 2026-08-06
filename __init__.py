"""Reverse engineering toolkit for Football Manager tactic files."""

from organiseMyProjects.logUtils import getApplication, setApplication

try:
    getApplication()
except RuntimeError:
    setApplication("fmsat")

from fmsat.parser import FMFParser, FMFTactic
from fmsat.structures import FileInspection, TacticMetadata

__all__ = ["FMFTactic", "FMFParser", "FileInspection", "TacticMetadata"]
