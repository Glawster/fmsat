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


def _position(slotId: str, roleCode: str, position: str):
    return SimpleNamespace(
        slotId=slotId,
        canonicalRole=roleCode,
        canonicalPosition=position,
        identity=SimpleNamespace(value=position),
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
        inPossession=SimpleNamespace(
            positions=(_position("slot-one", "inRole", "AMC"),)
        ),
        outOfPossession=SimpleNamespace(
            positions=(_position("slot-one", "outRole", "MC"),)
        ),
    )

    depth = RoleDepthService("phaseMean").depthBuild(tactic, roles)

    alpha = next(
        candidate
        for candidate in depth[0].candidates
        if candidate.player.name == "Alpha"
    )
    assert alpha.score == 70.0
    assert tuple(item.roleCode for item in alpha.roleFits) == ("inRole", "outRole")


def testRoleDepthIsUnavailableWhenSlotLinkageEvidenceIsMissing() -> None:
    """Do not infer simultaneous slots by ordinal when durable slot linkage is absent."""

    role = _role("role", "Role", "R", {"Alpha": 80.0})
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(
            positions=(SimpleNamespace(
                slotId=None,
                canonicalRole="role",
                canonicalPosition="AMC",
                identity=SimpleNamespace(value="AMC"),
            ),)
        ),
        outOfPossession=SimpleNamespace(
            positions=(SimpleNamespace(
                slotId=None,
                canonicalRole="role",
                canonicalPosition="MC",
                identity=SimpleNamespace(value="MC"),
            ),)
        ),
    )

    depth = RoleDepthService("phaseMean").depthBuild(tactic, {"role": role})

    assert len(depth) == 1
    assert depth[0].bestCandidate is None
    assert depth[0].uncovered
    assert "slot linkage is unavailable" in depth[0].unavailableReason


def testRoleDepthIsUnavailableWithoutExplicitAggregationPolicy() -> None:
    """A multi-phase slot score must not be invented when its policy is missing."""

    role = _role("role", "Role", "R", {"Alpha": 80.0})
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(
            positions=(_position("slot-one", "role", "AMC"),)
        ),
        outOfPossession=SimpleNamespace(
            positions=(_position("slot-one", "role", "MC"),)
        ),
    )

    depth = RoleDepthService().depthBuild(tactic, {"role": role})

    assert depth[0].bestCandidate is None
    assert depth[0].uncovered
    assert depth[0].unavailableReason == "Required slot aggregation policy is unavailable"
