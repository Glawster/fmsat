from __future__ import annotations

from enum import Enum


class PositionIdentity(Enum):
    """Football Manager tactical position identities used in formations."""

    GK = "GK"

    DL = "DL"
    DC = "DC"
    DR = "DR"

    WBL = "WBL"
    WBR = "WBR"

    DM = "DM"

    ML = "ML"
    MC = "MC"
    MR = "MR"

    AML = "AML"
    AMC = "AMC"
    AMR = "AMR"

    ST = "ST"
