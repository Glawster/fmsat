"""Regression coverage for mirrored tactic-slot linkage."""

from fmsat.core.tacticSlots import slotsLink
from fmsat.football.role import Role
from fmsat.football.roleIdentity import RoleIdentity
from fmsat.football.roleProfile import RoleProfile
from fmsat.tactics.formation import Formation
from fmsat.tactics.position import Position
from fmsat.tactics.positionIdentity import PositionIdentity
from fmsat.tactics.tactic import Tactic


def _position(slotId: str, identity: str, canonical: str) -> Position:
    return Position(
        identity=PositionIdentity[identity],
        role=Role(RoleIdentity.UNRESOLVED),
        roleProfile=RoleProfile(name="Observed role"),
        slotId=slotId,
        canonicalPosition=canonical,
    )


def testSlotsLinkRepairsCrossedMirroredDmDurableIds() -> None:
    """DMCL/DMCR canonical evidence must prevent a crossed left/right pairing."""

    ipLeft = _position("slot-a", "DM", "DMCL")
    ipRight = _position("slot-b", "DM", "DMCR")
    oopLeft = _position("slot-b", "DM", "DMCL")
    oopRight = _position("slot-a", "DM", "DMCR")
    tactic = Tactic(
        name="crossed-dm",
        inPossession=Formation(name="IP", positions=[ipLeft, ipRight]),
        outOfPossession=Formation(name="OOP", positions=[oopLeft, oopRight]),
    )

    slots = slotsLink(tactic)

    left = next(slot for slot in slots if slot.ipPosition is ipLeft)
    right = next(slot for slot in slots if slot.ipPosition is ipRight)
    assert left.oopPosition is oopLeft
    assert right.oopPosition is oopRight


def testSlotsLinkKeepsRealFamilyChangeDespiteDifferentCanonicalPositions() -> None:
    """AMR -> MR remains a real transition rather than being forced to exact code."""

    ip = _position("slot-wide", "AMR", "AMR")
    oop = _position("slot-wide", "MR", "MR")
    tactic = Tactic(
        name="family-change",
        inPossession=Formation(name="IP", positions=[ip]),
        outOfPossession=Formation(name="OOP", positions=[oop]),
    )

    slots = slotsLink(tactic)

    assert len(slots) == 1
    assert slots[0].ipPosition is ip
    assert slots[0].oopPosition is oop
