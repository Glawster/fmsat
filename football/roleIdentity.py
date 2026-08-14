"""
Football Manager role identities.

These identities represent the standard Football Manager roles recognised by
FMSAT. They are used throughout the object model to identify a role and are
shared by all tactics.
"""

from enum import StrEnum


class RoleIdentity(StrEnum):
    """Football Manager role identities."""

    BCB = "BCB"  # Ball Playing Central Defender
    DLP = "DLP"  # Deep Lying Playmaker
    CB = "CB"  # Central Defender
    HB = "HB"  # Half Back
    WB = "WB"  # Wing Back
    DM = "DM"  # Defensive Midfielder
    CM = "CM"  # Central Midfielder
    AM = "AM"  # Attacking Midfielder
    IF = "IF"  # Inside Forward
    W = "W"  # Winger
    CF = "CF"  # Centre Forward
    GK = "GK"  # Goalkeeper
    UNRESOLVED = "UNRESOLVED"  # Observed role awaiting a user-supplied definition
