"""Tests for simultaneous tactic-slot role depth in requirement 007B."""

from types import SimpleNamespace

from fmsat.core.roleDepth import RoleDepthService
from fmsat.core.squadAssessment import GenericRoleFit, RoleCandidate
from fmsat.core.squadModel import SquadModelPlayer


def _player(name: str) -> SquadModelPlayer:
    return SquadModelPlayer(
        name=name,
        positions="",
        ca="",
        pa="",
        confidence=1.0,
        attributes=(),
    )


def _role(
    roleCode: str,
    displayName: str,
    abbreviation: str,
    scores: dict[str, float | None],
):
    return SimpleNamespace(
        roleCode=roleCode,
        displayName=displayName,
        abbreviation=abbreviation,
        candidates=tuple(
            RoleCandidate(
                _player(name),
                GenericRoleFit(
                    score,
                    None if score is not None else "Missing attributes",
                    (),
                ),
            )
            for name, score in scores.items()
        ),
    )


def _position(
    slotId: str | None,
    roleCode: str | None,
    position: str,
    x: float | None = None,
    y: float | None = None,
    observedRole: str | None = None,
):
    return SimpleNamespace(
        slotId=slotId,
        canonicalRole=roleCode,
        canonicalPosition=position,
        identity=SimpleNamespace(value=position),
        roleProfile=SimpleNamespace(name=observedRole or "Observed role"),
        x=x,
        y=y,
    )


def testRoleDepthUsesUniquePlayersAcrossSimultaneousPrimarySlots() -> None:
    """One high-scoring player must not be assigned to two simultaneous slots."""

    roles = {
        "leftRole": _role(
            "leftRole",
            "Left Role",
            "LR",
            {"Alpha": 90.0, "Bravo": 80.0, "Charlie": 40.0, "Delta": 30.0},
        ),
        "rightRole": _role(
            "rightRole",
            "Right Role",
            "RR",
            {"Alpha": 95.0, "Bravo": 70.0, "Charlie": 60.0, "Delta": 50.0},
        ),
    }
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(
            positions=(
                _position("slot-left", "leftRole", "AML"),
                _position("slot-right", "rightRole", "AMR"),
            )
        ),
        outOfPossession=SimpleNamespace(
            positions=(
                _position("slot-left", "leftRole", "ML"),
                _position("slot-right", "rightRole", "MR"),
            )
        ),
    )

    depth = RoleDepthService("phaseMean").depthBuild(tactic, roles)

    assert len(depth) == 2
    assert {slot.bestCandidate for slot in depth} == {"Alpha", "Bravo"}
    assert len({slot.bestCandidate for slot in depth}) == 2


def testRoleDepthBackupLayerExcludesEveryPrimaryAssignment() -> None:
    """Backups must be independent depth rather than starters borrowed from another slot."""

    roles = {
        "leftRole": _role(
            "leftRole",
            "Left Role",
            "LR",
            {"Alpha": 90.0, "Bravo": 80.0, "Charlie": 70.0, "Delta": 60.0},
        ),
        "rightRole": _role(
            "rightRole",
            "Right Role",
            "RR",
            {"Alpha": 95.0, "Bravo": 85.0, "Charlie": 75.0, "Delta": 65.0},
        ),
    }
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(
            positions=(
                _position("slot-left", "leftRole", "AML"),
                _position("slot-right", "rightRole", "AMR"),
            )
        ),
        outOfPossession=SimpleNamespace(
            positions=(
                _position("slot-left", "leftRole", "ML"),
                _position("slot-right", "rightRole", "MR"),
            )
        ),
    )

    depth = RoleDepthService("phaseMean").depthBuild(tactic, roles)

    primary = {slot.bestCandidate for slot in depth}
    backups = {slot.backupCandidate for slot in depth}
    assert None not in primary
    assert None not in backups
    assert primary.isdisjoint(backups)
    assert len(backups) == 2


def testRoleDepthAveragesPhaseRoleFitsAndRetainsEachRoleEvidence() -> None:
    """A slot changing role by phase should expose both Generic Role Fit inputs."""

    roles = {
        "inRole": _role("inRole", "In Role", "IR", {"Alpha": 80.0, "Bravo": 60.0}),
        "outRole": _role("outRole", "Out Role", "OR", {"Alpha": 60.0, "Bravo": 80.0}),
    }
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(positions=(_position("slot-one", "inRole", "AMC"),)),
        outOfPossession=SimpleNamespace(positions=(_position("slot-one", "outRole", "MC"),)),
    )

    depth = RoleDepthService("phaseMean").depthBuild(tactic, roles)

    alpha = next(candidate for candidate in depth[0].candidates if candidate.player.name == "Alpha")
    assert alpha.score == 70.0
    assert tuple(item.roleCode for item in alpha.roleFits) == ("inRole", "outRole")


def testRoleDepthResolvesLegacyAbbreviationToSemanticCatalogueRole() -> None:
    """Persisted abbreviation identities must reuse canonical role-fit evidence."""

    halfBack = _role("halfBack", "Half-Back", "HB", {"Alpha": 80.0})
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(positions=(_position("slot-one", "HB", "DM"),)),
        outOfPossession=SimpleNamespace(positions=(_position("slot-one", "HB", "DM"),)),
    )

    depth = RoleDepthService("phaseMean").depthBuild(tactic, {"halfBack": halfBack})

    assert depth[0].roles[0].roleCode == "halfBack"
    assert depth[0].roles[0].abbreviation == "HB"
    assert depth[0].bestCandidate == "Alpha"


def testRoleDepthRetainsObservedAbbreviationWhenSemanticRoleIsUnresolved() -> None:
    """Known FM text such as TW must remain visible even before role knowledge is confirmed."""

    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(positions=(_position("slot-one", "insideForward", "AML"),)),
        outOfPossession=SimpleNamespace(
            positions=(_position("slot-one", None, "AML", observedRole="TW"),)
        ),
    )
    insideForward = _role("insideForward", "Inside Forward", "IF", {"Alpha": 80.0})

    depth = RoleDepthService("phaseMean").depthBuild(
        tactic,
        {"insideForward": insideForward},
    )

    oop = next(role for role in depth[0].roles if role.phase == "OOP")
    assert oop.roleCode is None
    assert oop.abbreviation == "TW"
    assert depth[0].bestCandidate is None
    assert "OOP roleCode is unavailable" in depth[0].unavailableReason


def testRoleDepthRecoversObservedRoleAfterRejectingPositionIdentity() -> None:
    """A leaked AMC position must not hide the retained AM role evidence."""

    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(
            positions=(_position("slot-one", "AMC", "AMC", observedRole="AM"),)
        ),
        outOfPossession=SimpleNamespace(
            positions=(_position("slot-one", "trackingAttackingMidfielder", "AMC"),)
        ),
    )
    tracking = _role(
        "trackingAttackingMidfielder", "Tracking Attacking Midfielder", "TAM", {"Alpha": 80.0}
    )
    attacking = _role("attackingMidfielder", "Attacking Midfielder", "AM", {"Alpha": 70.0})

    depth = RoleDepthService("phaseMean").depthBuild(
        tactic,
        {
            "attackingMidfielder": attacking,
            "trackingAttackingMidfielder": tracking,
        },
    )

    assert depth[0].roles[0].roleCode == "attackingMidfielder"
    assert depth[0].roles[1].roleCode == "trackingAttackingMidfielder"
    assert depth[0].bestCandidate == "Alpha"


def testRoleDepthConsumesEveryTacticPhaseAssignmentBySemanticCode() -> None:
    """The phase assignments entering Roles and Role Depth must be identical."""

    ipCodes = tuple(f"ipRole{index}" for index in range(8))
    oopCodes = tuple(f"oopRole{index}" for index in range(8))
    catalogue = {code: _role(code, code, code, {"Alpha": 70.0}) for code in (*ipCodes, *oopCodes)}
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(
            positions=tuple(
                _position(f"slot-{index}", code, f"P{index}") for index, code in enumerate(ipCodes)
            )
        ),
        outOfPossession=SimpleNamespace(
            positions=tuple(
                _position(f"slot-{index}", code, f"P{index}") for index, code in enumerate(oopCodes)
            )
        ),
    )

    depth = RoleDepthService("phaseMean").depthBuild(tactic, catalogue)

    consumed = tuple(
        (slot.slotId, requirement.phase, requirement.roleCode)
        for slot in depth
        for requirement in slot.roles
    )
    expected = tuple(
        (f"slot-{index}", phase, codes[index])
        for index in range(8)
        for phase, codes in (("IP", ipCodes), ("OOP", oopCodes))
    )
    assert consumed == expected


def testRoleDepthIsUnavailableWhenSlotLinkageEvidenceIsMissing() -> None:
    """Do not infer simultaneous slots by ordinal when durable slot linkage is absent."""

    role = _role("role", "Role", "R", {"Alpha": 80.0})
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(positions=(_position(None, "role", "AMC"),)),
        outOfPossession=SimpleNamespace(positions=(_position(None, "role", "MC"),)),
    )

    depth = RoleDepthService("phaseMean").depthBuild(tactic, {"role": role})

    assert len(depth) == 1
    assert depth[0].bestCandidate is None
    assert depth[0].uncovered
    assert "slot linkage is unavailable" in depth[0].unavailableReason
    assert [requirement.roleCode for requirement in depth[0].roles] == ["role"]
    assert depth[0].roles[0].phase == "IP"


def testRoleDepthPreservesTenDurablePairsWhenOnePhaseSlotIsMissing() -> None:
    """One broken phase link must not invalidate ten independently linked slots."""

    role = _role("role", "Role", "R", {"Alpha": 80.0})
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(
            positions=tuple(_position(f"slot-{index:02d}", "role", "MC") for index in range(1, 12))
        ),
        outOfPossession=SimpleNamespace(
            positions=(
                *(_position(f"slot-{index:02d}", "role", "MC") for index in range(1, 11)),
                _position(None, "role", "MC"),
            )
        ),
    )

    depth = RoleDepthService("phaseMean").depthBuild(tactic, {"role": role})

    linked = [slot for slot in depth if not slot.slotId.startswith("unlinked:")]
    broken = [slot for slot in depth if slot.slotId.startswith("unlinked:")]
    assert len(depth) == 11
    assert [slot.slotId for slot in linked] == [f"slot-{index:02d}" for index in range(1, 11)]
    assert all(
        [requirement.phase for requirement in slot.roles] == ["IP", "OOP"] for slot in linked
    )
    assert all(slot.candidates for slot in linked)
    assert len(broken) == 1
    assert broken[0].roles[0].phase == "IP"
    assert broken[0].candidates == ()
    assert "slot linkage is unavailable" in broken[0].unavailableReason


def testRoleDepthRecoversGloballyUnambiguousSpatialLinkage() -> None:
    """Regenerated phase slots can recover linkage from unique global geometry."""

    roles = {
        "leftIn": _role("leftIn", "Left In", "LI", {"Alpha": 80.0, "Bravo": 70.0}),
        "rightIn": _role("rightIn", "Right In", "RI", {"Alpha": 70.0, "Bravo": 80.0}),
        "leftOut": _role("leftOut", "Left Out", "LO", {"Alpha": 80.0, "Bravo": 70.0}),
        "rightOut": _role("rightOut", "Right Out", "RO", {"Alpha": 70.0, "Bravo": 80.0}),
    }
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(
            positions=(
                _position("ip-left", "leftIn", "AML", 0.20, 0.30),
                _position("ip-right", "rightIn", "AMR", 0.80, 0.30),
            )
        ),
        outOfPossession=SimpleNamespace(
            positions=(
                _position("oop-right", "rightOut", "MR", 0.78, 0.46),
                _position("oop-left", "leftOut", "ML", 0.22, 0.46),
            )
        ),
    )

    depth = RoleDepthService("phaseMean").depthBuild(tactic, roles)

    assert len(depth) == 2
    assert [tuple(role.roleCode for role in slot.roles) for slot in depth] == [
        ("leftIn", "leftOut"),
        ("rightIn", "rightOut"),
    ]
    assert all(slot.slotId.startswith("spatial:") for slot in depth)


def testRoleDepthRejectsAmbiguousSpatialLinkage() -> None:
    """Spatial recovery must remain unavailable when two complete mappings are equivalent."""

    role = _role("role", "Role", "R", {"Alpha": 80.0})
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(
            positions=(
                _position("ip-a", "role", "MC", 0.40, 0.40),
                _position("ip-b", "role", "MC", 0.60, 0.40),
            )
        ),
        outOfPossession=SimpleNamespace(
            positions=(
                _position("oop-a", "role", "MC", 0.50, 0.50),
                _position("oop-b", "role", "MC", 0.50, 0.50),
            )
        ),
    )

    depth = RoleDepthService("phaseMean").depthBuild(tactic, {"role": role})

    assert len(depth) == 2
    assert all(slot.bestCandidate is None for slot in depth)
    assert all("slot linkage is unavailable" in slot.unavailableReason for slot in depth)
    assert all(slot.roles and slot.roles[0].roleCode == "role" for slot in depth)


def testRoleDepthIsUnavailableWithoutExplicitAggregationPolicy() -> None:
    """A multi-phase slot score must not be invented when its policy is missing."""

    role = _role("role", "Role", "R", {"Alpha": 80.0})
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(positions=(_position("slot-one", "role", "AMC"),)),
        outOfPossession=SimpleNamespace(positions=(_position("slot-one", "role", "MC"),)),
    )

    depth = RoleDepthService().depthBuild(tactic, {"role": role})

    assert depth[0].bestCandidate is None
    assert depth[0].uncovered
    assert depth[0].unavailableReason == "Required slot aggregation policy is unavailable"


def testRoleDepthRecoversRoleFromObservedProfileDescription() -> None:
    """Role depth must use the same retained FM role evidence as squad assessment."""

    position = SimpleNamespace(
        canonicalRole=None,
        canonicalPosition="STC",
        identity=SimpleNamespace(value="STC"),
        roleProfile=SimpleNamespace(
            name="Observed role",
            description="CFD (Observed role)",
        ),
    )

    roleCatalogue = {
        "centreForward": SimpleNamespace(
            abbreviation="CFD",
            displayName="Centre Forward",
        )
    }

    assert RoleDepthService._roleCodeResolve(position, roleCatalogue) == "centreForward"


def testRoleDepthDoesNotUsePositionAsRoleIdentity() -> None:
    position = SimpleNamespace(
        canonicalRole="AMC",
        canonicalPosition="AMC",
        identity=SimpleNamespace(value="AMC"),
        roleProfile=SimpleNamespace(
            name="Observed role",
            description="AM (Observed role)",
        ),
    )

    roleCatalogue = {
        "attackingMidfielder": SimpleNamespace(
            abbreviation="AM",
            displayName="Attacking Midfielder",
        )
    }

    assert RoleDepthService._roleCodeResolve(position, roleCatalogue) == "attackingMidfielder"
