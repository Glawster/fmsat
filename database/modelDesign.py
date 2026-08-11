"""Football Object Model.

Python translation of modelDesign.ads.

The model describes football concepts and their relationships. Runtime
discovery layers may populate values such as instruction names, instruction
values, role-profile text, attributes, traits, and behaviours from Football
Manager screenshots or persisted football knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


Text = str


class RoleIdentity(Enum):
    """Football Manager role identities recognised by the model. To be discovered at runtime."""

    BCB = "BCB"
    DLP = "DLP"
    CB = "CB"
    HB = "HB"
    WB = "WB"
    DM = "DM"
    CM = "CM"
    AM = "AM"
    W = "W"
    CF = "CF"


@dataclass
class Attribute:
    """One Football Manager attribute and its weighting."""

    name: Text
    weighting: int


AttributeList = list[Attribute]


@dataclass
class Trait:
    """One player trait."""

    name: Text
    description: Text


TraitList = list[Trait]


InstructionValueList = list[Text]


@dataclass
class Instruction:
    """An instruction and the values Football Manager allows for it."""

    name: Text
    values: InstructionValueList = field(default_factory=list)


TeamInstructionList = list[Instruction]
PlayerInstructionList = list[Instruction]


@dataclass
class Role:
    """A reusable Football Manager role."""

    name: RoleIdentity
    description: Text


@dataclass
class Behaviour:
    """One behaviour associated with a role profile."""

    name: Text
    description: Text


BehaviourList = list[Behaviour]


@dataclass
class RoleProfile:
    """The detailed profile of a role as presented by Football Manager."""

    name: Text
    description: Text
    behaviours: BehaviourList = field(default_factory=list)
    keyAttributes: AttributeList = field(default_factory=list)
    keyTraits: TraitList = field(default_factory=list)
    instructions: PlayerInstructionList = field(default_factory=list)


@dataclass
class PositionNeeds:
    """Optional qualities sought from the player occupying a position."""

    name: Text
    description: Text


PositionNeedsList = list[PositionNeeds]


class PositionIdentity(Enum):
    """Football Manager tactical positions."""

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


@dataclass
class Position:
    """One position within a formation."""

    identity: PositionIdentity
    role: Role
    roleProfile: RoleProfile
    playerInstructions: PlayerInstructionList = field(default_factory=list)
    positionNeeds: PositionNeedsList = field(default_factory=list)


PositionList = list[Position]


@dataclass
class Formation:
    """A formation and the instructions applying to it."""

    name: Text
    positions: PositionList = field(default_factory=list)
    teamInstructions: TeamInstructionList = field(default_factory=list)


@dataclass
class Transition:
    """How the team reacts when possession changes.

    The Football Object Model intentionally leaves this empty until the
    relevant Football Manager concepts are defined.
    """

    """ This is probably a subset of the team instructions, but the model does not yet know which ones. """
    transitionList: list[Instruction] = field(default_factory=list)


@dataclass
class Tactic:
    """A complete football tactic."""

    inPossession: Formation
    outOfPossession: Formation
    transition: Transition = field(default_factory=Transition)
