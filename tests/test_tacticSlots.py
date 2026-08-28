"""Position pairing for simultaneous tactic slots in requirement 011."""

from pathlib import Path

import fmsat.core.tacticSlots as tacticSlotsModule
from fmsat.core.tacticSlots import slotsLink, slotSortKey
from fmsat.football.role import Role
from fmsat.football.roleIdentity import RoleIdentity
from fmsat.football.roleProfile import RoleProfile
from fmsat.tactics.formation import Formation
from fmsat.tactics.position import Position
from fmsat.tactics.positionIdentity import PositionIdentity
from fmsat.tactics.tactic import Tactic


def _position(
    slotId: str | None,
    identity: str,
    x: float | None = None,
    y: float | None = None,
    *,
    canonical: str | None = None,
    footballer: str = "Must not be consumed",
) -> Position:
    return Position(
        identity=PositionIdentity[identity],
        role=Role(RoleIdentity.UNRESOLVED),
        roleProfile=RoleProfile(name="Observed role"),
        slotId=slotId,
        x=x,
        y=y,
        canonicalPosition=canonical or identity,
        player=footballer,
    )


def _tactic(ip: tuple[Position, ...], oop: tuple[Position, ...] = ()) -> Tactic:
    return Tactic(
        name="pairing-fixture",
        inPossession=Formation(name="IP", positions=list(ip)),
        outOfPossession=Formation(name="OOP", positions=list(oop)),
    )


def testSlotsLinkPairsByDurableSlotIdIndependentOfListOrder() -> None:
    """Matching unique slotId values are simultaneous even when list order differs."""

    tactic = _tactic(
        (
            _position("slot-left", "AML", 0.20, 0.30),
            _position("slot-right", "AMR", 0.80, 0.30),
        ),
        (
            _position("slot-right", "MR", 0.80, 0.50),
            _position("slot-left", "ML", 0.20, 0.50),
        ),
    )

    slots = slotsLink(tactic)

    assert [(slot.slotId, slot.unavailableReason) for slot in slots] == [
        ("slot-left", None),
        ("slot-right", None),
    ]
    assert slots[0].ipPosition is tactic.inPossession.positions[0]
    assert slots[0].oopPosition is tactic.outOfPossession.positions[1]
    assert slots[1].ipPosition is tactic.inPossession.positions[1]
    assert slots[1].oopPosition is tactic.outOfPossession.positions[0]


def testSlotsLinkRecoversGloballyUnambiguousSpatialLinkage() -> None:
    """Regenerated phase slots can recover linkage from unique global geometry."""

    tactic = _tactic(
        (
            _position("ip-left", "AML", 0.20, 0.30),
            _position("ip-right", "AMR", 0.80, 0.30),
        ),
        (
            _position("oop-right", "MR", 0.78, 0.46),
            _position("oop-left", "ML", 0.22, 0.46),
        ),
    )

    slots = slotsLink(tactic)

    assert [slot.slotId for slot in slots] == ["spatial:01", "spatial:02"]
    assert all(slot.unavailableReason is None for slot in slots)
    assert slots[0].ipPosition is tactic.inPossession.positions[0]
    assert slots[0].oopPosition is tactic.outOfPossession.positions[1]
    assert slots[1].ipPosition is tactic.inPossession.positions[1]
    assert slots[1].oopPosition is tactic.outOfPossession.positions[0]


def testSlotsLinkDoesNotOrdinalPairWhenIdsAndGeometryDisagree() -> None:
    """List index is not evidence: IP[i] must not pair with OOP[i] by default."""

    tactic = _tactic(
        (
            _position("ip-left", "AML", 0.20, 0.30),
            _position("ip-right", "AMR", 0.80, 0.30),
        ),
        (
            _position("oop-right", "MR", 0.80, 0.46),
            _position("oop-left", "ML", 0.20, 0.46),
        ),
    )

    slots = slotsLink(tactic)
    paired = {(id(slot.ipPosition), id(slot.oopPosition)) for slot in slots}

    assert (
        id(tactic.inPossession.positions[0]),
        id(tactic.outOfPossession.positions[0]),
    ) not in paired
    assert slots[0].oopPosition is tactic.outOfPossession.positions[1]
    assert slots[1].oopPosition is tactic.outOfPossession.positions[0]


def testSlotsLinkRejectsAmbiguousSpatialLinkage() -> None:
    """Spatial recovery stays Unavailable when two complete mappings are equivalent."""

    tactic = _tactic(
        (
            _position("ip-a", "MC", 0.40, 0.40),
            _position("ip-b", "MC", 0.60, 0.40),
        ),
        (
            _position("oop-a", "MC", 0.50, 0.50),
            _position("oop-b", "MC", 0.50, 0.50),
        ),
    )

    slots = slotsLink(tactic)

    assert len(slots) == 4
    assert all(slot.unavailableReason is not None for slot in slots)
    assert all("slot linkage is unavailable" in (slot.unavailableReason or "") for slot in slots)
    assert [slot.ipPosition is not None for slot in slots] == [True, True, False, False]
    assert [slot.oopPosition is not None for slot in slots] == [False, False, True, True]


def testSlotsLinkIsUnlinkedWhenSlotIdAndCoordinatesAreMissing() -> None:
    """Do not invent a partner when both durable id and geometry are absent."""

    tactic = _tactic(
        (_position(None, "AMC"),),
        (_position(None, "MC"),),
    )

    slots = slotsLink(tactic)

    assert len(slots) == 2
    assert all(slot.slotId.startswith("unlinked:") for slot in slots)
    assert slots[0].ipPosition is tactic.inPossession.positions[0]
    assert slots[0].oopPosition is None
    assert slots[1].ipPosition is None
    assert slots[1].oopPosition is tactic.outOfPossession.positions[0]
    assert all(
        "unambiguous spatial evidence is required" in (slot.unavailableReason or "")
        for slot in slots
    )


def testSlotsLinkOnePhaseLeavesTheOtherPositionNone() -> None:
    """An IP-only tactic is complete evidence of one phase, not a linkage failure."""

    tactic = _tactic((_position("slot-one", "AMC"),))

    slots = slotsLink(tactic)

    assert len(slots) == 1
    assert slots[0].slotId == "slot-one"
    assert slots[0].ipPosition is tactic.inPossession.positions[0]
    assert slots[0].oopPosition is None
    assert slots[0].unavailableReason is None


def testSlotsLinkKeepsTenDurablePairsAndLeavesEachBrokenPhaseUnlinked() -> None:
    """One missing id must not discard the independently valid durable pairs."""

    ip = tuple(_position(f"slot-{index:02d}", "MC") for index in range(1, 12))
    oop = tuple(_position(f"slot-{index:02d}", "MC") for index in range(1, 11)) + (
        _position(None, "MC"),
    )
    tactic = _tactic(ip, oop)

    slots = slotsLink(tactic)
    linked = [slot for slot in slots if slot.unavailableReason is None]
    broken = [slot for slot in slots if slot.unavailableReason is not None]

    assert [slot.slotId for slot in linked] == [f"slot-{index:02d}" for index in range(1, 11)]
    assert all(slot.ipPosition is not None and slot.oopPosition is not None for slot in linked)
    assert len(broken) == 2
    assert broken[0].ipPosition is ip[10]
    assert broken[0].oopPosition is None
    assert broken[1].ipPosition is None
    assert broken[1].oopPosition is oop[10]
    assert all("matching durable slotId" in (slot.unavailableReason or "") for slot in broken)


def testSlotSortKeyUsesIpCanonicalPositionAndBreaksAmlAmclTies() -> None:
    """Sort by the single IP-if-present code, not a combined display cell."""

    aml = slotsLink(_tactic((_position("slot-aml", "AML"),)))[0]
    amcl = slotsLink(_tactic((_position("slot-amcl", "AMC", canonical="AMCL"),)))[0]
    st = slotsLink(_tactic((_position("slot-st", "ST"),)))[0]
    dcLeft = slotsLink(_tactic((_position("slot-dcl", "DC", canonical="DCL"),)))[0]
    dcRight = slotsLink(_tactic((_position("slot-dcr", "DC", canonical="DCR"),)))[0]

    ordered = sorted((amcl, st, dcRight, aml, dcLeft), key=slotSortKey)
    assert [slot.slotId for slot in ordered] == [
        "slot-st",
        "slot-amcl",
        "slot-aml",
        "slot-dcl",
        "slot-dcr",
    ]
    assert slotSortKey(amcl)[0:2] == slotSortKey(aml)[0:2]


def testSlotsLinkDoesNotReadAnAssignedFootballer() -> None:
    """Pairing is tactic structure; an assigned name cannot change the result."""

    named = _tactic(
        (_position("slot-one", "AMC", footballer="Alpha"),),
        (_position("slot-one", "MC", footballer="Bravo"),),
    )
    anonymous = _tactic(
        (_position("slot-one", "AMC", footballer="Charlie"),),
        (_position("slot-one", "MC", footballer="Delta"),),
    )

    namedSlots = slotsLink(named)
    anonymousSlots = slotsLink(anonymous)

    assert namedSlots[0].slotId == anonymousSlots[0].slotId == "slot-one"
    assert namedSlots[0].unavailableReason is anonymousSlots[0].unavailableReason is None
    assert named.inPossession.positions[0].player == "Alpha"
    assert anonymous.inPossession.positions[0].player == "Charlie"


def testTacticSlotsModuleHasNoSquadOrUiDependencies() -> None:
    """Shared pairing must stay UI-independent and squad-free."""

    source = Path(tacticSlotsModule.__file__).read_text(encoding="utf-8")
    for forbidden in ("SquadModel", "BestXi", "PySide", "QtGui", "QtWidgets", "genericRoleFit"):
        assert forbidden not in source
