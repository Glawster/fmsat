from fmsat.app.squadDetailModel import CandidateDisplay, RoleDisplay
from fmsat.app.squadDetailTabOverrides import _candidateEligible


def _role(position: str) -> RoleDisplay:
    return RoleDisplay(
        roleCode="testRole",
        displayName="Test Role",
        abbreviation="TR",
        positions=position,
        phases="OOP",
        coverage="No Candidates found",
        candidates=(),
    )


def _candidate(positions: str) -> CandidateDisplay:
    return CandidateDisplay(
        name="Example Player",
        positions=positions,
        score="Unavailable",
        bestRole="Unavailable",
        breakdown="Unavailable",
        available=False,
    )


def testGoalkeeperFamilyOnlyAdmitsGoalkeepers() -> None:
    role = _role("GK")

    assert _candidateEligible(role, _candidate("GK")) is True
    assert _candidateEligible(role, _candidate("D (C)")) is False
    assert _candidateEligible(role, _candidate("D/WB (R)")) is False


def testFullBackAndWingBackFamiliesRemainDistinct() -> None:
    fullBack = _role("FB")
    wingBack = _role("WB")
    fullBackPlayer = _candidate("D (RL)")
    wingBackPlayer = _candidate("WB (RL)")

    assert _candidateEligible(fullBack, fullBackPlayer) is True
    assert _candidateEligible(fullBack, wingBackPlayer) is False
    assert _candidateEligible(wingBack, wingBackPlayer) is True
    assert _candidateEligible(wingBack, fullBackPlayer) is False


def testMultiFamilyRolesAdmitEitherSupportedPlayerFamily() -> None:
    winger = _role("MW, AMW")

    assert _candidateEligible(winger, _candidate("M (R)")) is True
    assert _candidateEligible(winger, _candidate("AM (L)")) is True
    assert _candidateEligible(winger, _candidate("D (R)")) is False
