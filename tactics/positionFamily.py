from __future__ import annotations

import re
from enum import Enum


class PositionFamily(Enum):
    """Canonical role-compatibility positions independent of pitch side."""

    GK = "GK"
    FB = "FB"
    WB = "WB"
    DC = "DC"
    DM = "DM"
    MC = "MC"
    MW = "MW"
    AMC = "AMC"
    AMW = "AMW"
    STC = "STC"


_EXACT_POSITION_FAMILY = {
    "GK": PositionFamily.GK,
    "DL": PositionFamily.FB,
    "DR": PositionFamily.FB,
    "WBL": PositionFamily.WB,
    "WBR": PositionFamily.WB,
    "DCL": PositionFamily.DC,
    "DC": PositionFamily.DC,
    "DCR": PositionFamily.DC,
    "DMCL": PositionFamily.DM,
    "DM": PositionFamily.DM,
    "DMCR": PositionFamily.DM,
    "MCL": PositionFamily.MC,
    "MC": PositionFamily.MC,
    "MCR": PositionFamily.MC,
    "ML": PositionFamily.MW,
    "MR": PositionFamily.MW,
    "AMCL": PositionFamily.AMC,
    "AMC": PositionFamily.AMC,
    "AMCR": PositionFamily.AMC,
    "AML": PositionFamily.AMW,
    "AMR": PositionFamily.AMW,
    "STCL": PositionFamily.STC,
    "STC": PositionFamily.STC,
    "STCR": PositionFamily.STC,
    "ST": PositionFamily.STC,
}


def positionFamilyFor(position: str) -> PositionFamily | None:
    """Return the family for one exact FM/FMSAT tactical position code."""

    return _EXACT_POSITION_FAMILY.get(position.strip().upper())


def playerPositionFamilies(positions: str) -> frozenset[PositionFamily]:
    """Convert compact Football Manager natural-position text into families.

    Examples include ``D (RLC)``, ``D/WB (R)``, ``M/AM (RL)`` and ``ST (C)``.
    Left/right detail is deliberately discarded because family compatibility is
    about the football position, not the side occupied by a tactic slot.
    """

    families: set[PositionFamily] = set()
    for rawGroup in positions.upper().split(","):
        group = re.sub(r"\s+", "", rawGroup)
        if not group:
            continue
        sideMatch = re.search(r"\(([LCR]+)\)$", group)
        sides = set(sideMatch.group(1)) if sideMatch else set()
        prefix = group[: sideMatch.start()] if sideMatch else group
        units = tuple(value for value in prefix.split("/") if value)
        for unit in units:
            if unit == "GK":
                families.add(PositionFamily.GK)
            elif unit == "WB":
                families.add(PositionFamily.WB)
            elif unit == "DM":
                families.add(PositionFamily.DM)
            elif unit == "AM":
                if sides & {"L", "R"}:
                    families.add(PositionFamily.AMW)
                if "C" in sides or not sides:
                    families.add(PositionFamily.AMC)
            elif unit == "M":
                if sides & {"L", "R"}:
                    families.add(PositionFamily.MW)
                if "C" in sides or not sides:
                    families.add(PositionFamily.MC)
            elif unit == "D":
                if sides & {"L", "R"}:
                    families.add(PositionFamily.FB)
                if "C" in sides or not sides:
                    families.add(PositionFamily.DC)
            elif unit == "ST":
                families.add(PositionFamily.STC)
    return frozenset(families)
