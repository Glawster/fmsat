from fmsat.core.parser import TacticVocabulary
from fmsat.core.rolePositionCompatibility import (
    RolePositionFamilyPolicy,
    rolePositionFamilies,
    roleSupportsPosition,
)
from fmsat.tactics.positionFamily import PositionFamily


def testKnownRolesUseConfiguredPositionFamilies() -> None:
    assert rolePositionFamilies("fullBack") == {PositionFamily.FB}
    assert rolePositionFamilies("wingBack") == {PositionFamily.WB}
    assert rolePositionFamilies("centreBack") == {PositionFamily.DC}
    assert rolePositionFamilies("deepLyingPlaymaker") == {
        PositionFamily.DM,
        PositionFamily.MC,
    }
    assert rolePositionFamilies("boxToBoxMidfielder") == {
        PositionFamily.DM,
        PositionFamily.MC,
    }
    assert rolePositionFamilies("winger") == {
        PositionFamily.MW,
        PositionFamily.AMW,
    }
    assert rolePositionFamilies("advancedPlaymaker") == {
        PositionFamily.MC,
        PositionFamily.AMC,
    }
    assert rolePositionFamilies("trackingCentreForward") == {
        PositionFamily.STC
    }


def testGoalkeeperRolesCannotBeValidatedAsDefenders() -> None:
    assert roleSupportsPosition("ballPlayingGoalkeeper", "GK") is True
    assert roleSupportsPosition("sweeperKeeper", "GK") is True
    assert roleSupportsPosition("ballPlayingGoalkeeper", "DC") is False
    assert roleSupportsPosition("sweeperKeeper", "DCR") is False


def testFullBackAndWingBackFamiliesAreDistinct() -> None:
    assert roleSupportsPosition("fullBack", "DL") is True
    assert roleSupportsPosition("fullBack", "DR") is True
    assert roleSupportsPosition("fullBack", "WBL") is False
    assert roleSupportsPosition("wingBack", "WBL") is True
    assert roleSupportsPosition("wingBack", "WBR") is True
    assert roleSupportsPosition("wingBack", "DL") is False


def testUnknownRoleOrPositionRemainsUnresolved() -> None:
    assert roleSupportsPosition("newRole", "DL") is None
    assert roleSupportsPosition("fullBack", "UNKNOWN") is None


def testPackagedPolicyContainsEveryKnownRole() -> None:
    policy = RolePositionFamilyPolicy.load()
    vocabulary = TacticVocabulary()

    assert policy.version == 1
    assert set(policy.roles) == set(vocabulary.roles)
