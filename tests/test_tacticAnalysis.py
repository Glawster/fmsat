"""Squad-independent tactic demand for requirement 011."""

from pathlib import Path

import fmsat.core.tacticAnalysis as tacticAnalysisModule
from fmsat.core.config import Configuration
from fmsat.core.parser import TacticVocabulary
from fmsat.app.tacticAnalysisDisplay import tacticAnalysisDisplayBuild
from fmsat.core.roleKnowledge import StoredRoleDefinition
from fmsat.core.tacticAnalysis import TacticAnalysisService, TRACKING_ROLE_CODES
from fmsat.football.role import Role
from fmsat.football.roleIdentity import RoleIdentity
from fmsat.football.roleProfile import RoleProfile
from fmsat.tactics.formation import Formation
from fmsat.tactics.position import Position
from fmsat.tactics.positionIdentity import PositionIdentity
from fmsat.tactics.tactic import Tactic


class _Knowledge:
    def __init__(
        self,
        weights: dict[str, dict[str, int]] | None = None,
        definitions: tuple[object, ...] = (),
    ) -> None:
        self.weights = weights or {}
        self.definitions = definitions

    def weightsLoad(self, roleIdentity: str | int) -> dict[str, int]:
        return dict(self.weights.get(str(roleIdentity), {}))

    def definitionsList(self) -> tuple[object, ...]:
        return self.definitions


def _position(
    slotId: str | None,
    identity: str,
    roleCode: str | None,
    *,
    observed: str | None = None,
    x: float | None = None,
    y: float | None = None,
    footballer: str = "Must not be consumed",
) -> Position:
    description = f"{observed} (Observed role)" if observed else ""
    return Position(
        identity=PositionIdentity[identity],
        role=Role(RoleIdentity.UNRESOLVED),
        roleProfile=RoleProfile(name="Observed role", description=description),
        slotId=slotId,
        x=x,
        y=y,
        canonicalPosition=identity,
        canonicalRole=roleCode,
        player=footballer,
    )


def _tactic(ip: tuple[Position, ...], oop: tuple[Position, ...] = ()) -> Tactic:
    return Tactic(
        name="demand-fixture",
        inPossession=Formation(name="IP", positions=list(ip)),
        outOfPossession=Formation(name="OOP", positions=list(oop)),
    )


def _service(weights: dict[str, dict[str, int]] | None = None) -> TacticAnalysisService:
    return TacticAnalysisService(
        TacticVocabulary(),
        _Knowledge(weights),  # type: ignore[arg-type]
        Configuration().activeAttributes,
        "test-policy",
    )


def testAnalysisBuildReturnsNoneWithoutATactic() -> None:
    assert _service().analysisBuild(None) is None


def testAnalysisSumsPackagedScaleWeightsByPhase() -> None:
    """A complete IP role that omits an attribute contributes 0, not Unavailable."""

    analysis = _service(
        {
            "insideForward": {"dribbling": 4, "finishing": 5},
            "trackingAttackingMidfielder": {"work_rate": 5, "stamina": 5},
        }
    ).analysisBuild(
        _tactic(
            (_position("slot-amc", "AMC", "insideForward"),),
            (_position("slot-amc", "AMC", "trackingAttackingMidfielder"),),
        )
    )

    assert analysis is not None
    assert analysis.scoringIdentity == "test-policy"
    assert analysis.weightExpectedPhaseRoles == 2
    assert analysis.weightCompletePhaseRoles == 2
    assert analysis.demandCoverageReason is None
    workRate = next(row for row in analysis.overallDemand if row.attribute == "work_rate")
    assert (workRate.overall, workRate.inPossession, workRate.outOfPossession) == (5, 0, 5)
    assert workRate.contributingPhaseRoles == 1
    assert tuple(
        (
            contributor.phase,
            contributor.canonicalPosition,
            contributor.roleCode,
            contributor.weight,
        )
        for contributor in workRate.contributors
    ) == (("OOP", "AMC", "trackingAttackingMidfielder", 5),)
    finishing = next(row for row in analysis.overallDemand if row.attribute == "finishing")
    assert (finishing.overall, finishing.inPossession, finishing.outOfPossession) == (5, 5, 0)
    assert analysis.slots[0].ipRole.resolutionState == "ready"
    assert analysis.slots[0].oopRole.resolutionState == "ready"
    assert analysis.slots[0].transition.classification == "roleChangeSameFamily"
    assert tacticAnalysisDisplayBuild(analysis).slots[0].evidence == "Ready"


def testAnalysisTreatsTrackingWingerWithoutWeightsAsRecognitionOnly() -> None:
    analysis = _service({"insideForward": {"dribbling": 4}}).analysisBuild(
        _tactic(
            (_position("slot-aml", "AML", "insideForward"),),
            (_position("slot-aml", "AML", "trackingWinger"),),
        )
    )

    assert analysis is not None
    assert analysis.slots[0].oopRole.resolutionState == "recognitionOnly"
    assert analysis.slots[0].oopRole.roleCode == "trackingWinger"
    assert analysis.weightCompletePhaseRoles == 1
    assert analysis.weightExpectedPhaseRoles == 2
    assert analysis.demandCoverageReason is not None
    assert "trackingWinger" in analysis.demandCoverageReason or "Tracking Winger" in (
        analysis.demandCoverageReason or ""
    )
    assert all(row.outOfPossession is None for row in analysis.overallDemand)


def testAnalysisIncludesPackagedTrackingAttackingMidfielderWeights() -> None:
    """TAM is assessmentRequired false but packaged 0-10 weights still count as ready."""

    packaged = Configuration().roleAssessmentWeights()
    analysis = _service(packaged).analysisBuild(
        _tactic(
            (_position("slot-amc", "AMC", "insideForward"),),
            (_position("slot-amc", "AMC", "trackingAttackingMidfielder"),),
        )
    )

    assert analysis is not None
    assert analysis.slots[0].oopRole.resolutionState == "ready"
    workRate = next(row for row in analysis.overallDemand if row.attribute == "work_rate")
    assert workRate.outOfPossession == packaged["trackingAttackingMidfielder"]["work_rate"]
    assert workRate.inPossession == 0


def testAnalysisOnePhaseMarksTheMissingPhaseWithoutInventingAPartner() -> None:
    analysis = _service({"insideForward": {"dribbling": 4}}).analysisBuild(
        _tactic((_position("slot-aml", "AML", "insideForward"),))
    )

    assert analysis is not None
    assert analysis.weightExpectedPhaseRoles == 1
    assert analysis.slots[0].oopRole.resolutionState == "missingPhase"
    assert analysis.slots[0].oopRole.roleCode is None
    assert analysis.slots[0].transition.classification == "unavailable"
    assert analysis.slots[0].linkageUnavailableReason is None
    assert analysis.weightCompletePhaseRoles == 1
    assert tacticAnalysisDisplayBuild(analysis).slots[0].evidence == "Partial"


def testAnalysisUnlinkedElevenPlusElevenExpectsTwentyTwoPhaseRoles() -> None:
    ip = tuple(_position(None, "MC", "insideForward") for _ in range(11))
    oop = tuple(_position(None, "MC", "attackingMidfielder") for _ in range(11))
    analysis = _service(
        {
            "insideForward": {"dribbling": 4},
            "attackingMidfielder": {"passing": 3},
        }
    ).analysisBuild(_tactic(ip, oop))

    assert analysis is not None
    assert analysis.weightExpectedPhaseRoles == 22
    assert analysis.slotCount == 22
    assert analysis.weightCompletePhaseRoles == 22
    assert all(slot.transition.classification == "unavailable" for slot in analysis.slots)
    assert all(slot.linkageUnavailableReason for slot in analysis.slots)
    assert analysis.overallDemand


def testAnalysisDoesNotOrdinalPairWhenIdsAndGeometryDisagree() -> None:
    analysis = _service(
        {
            "insideForward": {"dribbling": 4},
            "winger": {"crossing": 3},
            "trackingWinger": {},
            "trackingWideMidfielder": {},
        }
    ).analysisBuild(
        _tactic(
            (
                _position("ip-left", "AML", "insideForward", x=0.20, y=0.30),
                _position("ip-right", "AMR", "winger", x=0.80, y=0.30),
            ),
            (
                _position("oop-right", "MR", "trackingWideMidfielder", x=0.80, y=0.46),
                _position("oop-left", "ML", "trackingWideMidfielder", x=0.20, y=0.46),
            ),
        )
    )

    assert analysis is not None
    left = next(slot for slot in analysis.slots if slot.canonicalPosition == "AML")
    assert left.oopRole.canonicalPosition == "ML"
    assert left.ipRole.roleCode == "insideForward"


def testAnalysisIgnoresAnAssignedFootballer() -> None:
    weights = {"insideForward": {"dribbling": 4}, "winger": {"crossing": 3}}
    named = _service(weights).analysisBuild(
        _tactic(
            (_position("slot-one", "AMC", "insideForward", footballer="Alpha"),),
            (_position("slot-one", "MC", "winger", footballer="Bravo"),),
        )
    )
    anonymous = _service(weights).analysisBuild(
        _tactic(
            (_position("slot-one", "AMC", "insideForward", footballer="Charlie"),),
            (_position("slot-one", "MC", "winger", footballer="Delta"),),
        )
    )

    assert named is not None and anonymous is not None
    assert named.overallDemand == anonymous.overallDemand
    assert named.observations == anonymous.observations
    assert named.slots[0].ipRole.roleCode == anonymous.slots[0].ipRole.roleCode
    source = Path(tacticAnalysisModule.__file__).read_text(encoding="utf-8")
    assert "Alpha" not in source
    for text in (
        named.tacticName,
        *(slot.ipRole.displayName for slot in named.slots),
        *(observation.explanation for observation in named.observations),
    ):
        assert "Alpha" not in text
        assert "Charlie" not in text


def testAnalysisLeavesUnknownCanonicalRoleUnresolved() -> None:
    """Unrecognised canonicalRole is not a role identity and must not look like missing weights."""

    analysis = _service({"insideForward": {"dribbling": 4}}).analysisBuild(
        _tactic((_position("slot-one", "AML", "someUnknownFutureRole"),))
    )

    assert analysis is not None
    assert analysis.slots[0].ipRole.roleCode is None
    assert analysis.slots[0].ipRole.resolutionState == "unresolved"
    assert analysis.slots[0].ipRole.abbreviation == "Unknown"
    assert analysis.overallDemand == ()


def testAnalysisResolvesAUniqueConfirmedDefinition() -> None:
    definition = StoredRoleDefinition(
        roleCode="customChannelRunner",
        displayName="Channel Runner",
        abbreviations=("CRN",),
        positions=("AML",),
        duties=(),
        behaviours=(),
    )
    analysis = TacticAnalysisService(
        TacticVocabulary(),
        _Knowledge({"customChannelRunner": {"pace": 4}}, (definition,)),  # type: ignore[arg-type]
        Configuration().activeAttributes,
        "test-policy",
    ).analysisBuild(_tactic((_position("slot-one", "AML", "CRN"),)))

    assert analysis is not None
    assert analysis.slots[0].ipRole.roleCode == "customChannelRunner"
    assert analysis.slots[0].ipRole.resolutionState == "ready"


def testAnalysisKeepsObservedAbbreviationWhenRoleIsUnresolved() -> None:
    analysis = _service().analysisBuild(
        _tactic((_position("slot-one", "AML", None, observed="ZZ"),))
    )

    assert analysis is not None
    assert analysis.slots[0].ipRole.resolutionState == "unresolved"
    assert analysis.slots[0].ipRole.abbreviation == "ZZ"
    assert analysis.slots[0].ipRole.roleCode is None
    assert analysis.overallDemand == ()


def testAnalysisStripsZeroWeightsAndRejectsOutOfScaleValues() -> None:
    ready = _service({"insideForward": {"dribbling": 4, "finishing": 0}}).analysisBuild(
        _tactic((_position("slot-one", "AML", "insideForward"),))
    )
    invalid = _service({"insideForward": {"dribbling": 11}}).analysisBuild(
        _tactic((_position("slot-one", "AML", "insideForward"),))
    )

    assert ready is not None
    assert ready.slots[0].ipRole.resolutionState == "ready"
    assert "finishing" not in (ready.slots[0].ipRole.weights or {})
    assert invalid is not None
    assert invalid.slots[0].ipRole.resolutionState == "missingWeights"
    assert invalid.overallDemand == ()


def testAnalysisReportsRepeatedRolesAndOmitsUniqueOnes() -> None:
    analysis = _service(
        {"insideForward": {"dribbling": 4}, "winger": {"crossing": 3}}
    ).analysisBuild(
        _tactic(
            (
                _position("slot-left", "AML", "insideForward"),
                _position("slot-right", "AMR", "insideForward"),
            )
        )
    )

    assert analysis is not None
    repeated = tuple(item for item in analysis.observations if item.code == "repeatedRole")
    assert len(repeated) == 1
    assert repeated[0].phase == "IP"
    assert repeated[0].title == "Inside Forward"
    assert "AML" in repeated[0].explanation and "AMR" in repeated[0].explanation
    assert all(
        item.code != "repeatedRole" or "Winger" not in item.title for item in analysis.observations
    )


def testAnalysisReportsAsymmetricFlanksOnlyWhenBothSidesExist() -> None:
    analysis = _service(
        {"insideForward": {"dribbling": 4}, "winger": {"crossing": 3}}
    ).analysisBuild(
        _tactic(
            (
                _position("slot-left", "AML", "insideForward"),
                _position("slot-right", "AMR", "winger"),
            )
        )
    )
    noPair = _service({"insideForward": {"dribbling": 4}}).analysisBuild(
        _tactic((_position("slot-left", "AML", "insideForward"),))
    )

    assert analysis is not None and noPair is not None
    flanks = tuple(item for item in analysis.observations if item.code == "asymmetricFlank")
    assert len(flanks) == 1
    assert flanks[0].phase == "IP"
    assert flanks[0].title == "AML/AMR"
    assert "Inside Forward" in flanks[0].explanation
    assert "Winger" in flanks[0].explanation
    assert all(item.code != "asymmetricFlank" for item in noPair.observations)


def testAnalysisCountsTrackingRolesFromTheClosedPackagedSet() -> None:
    analysis = _service(
        {
            "insideForward": {"dribbling": 4},
            "trackingAttackingMidfielder": {"work_rate": 5},
        }
    ).analysisBuild(
        _tactic(
            (_position("slot-amc", "AMC", "insideForward"),),
            (_position("slot-amc", "AMC", "trackingAttackingMidfielder"),),
        )
    )

    assert analysis is not None
    tracking = next(item for item in analysis.observations if item.code == "trackingRoleCount")
    assert tracking.phase == ""
    assert tracking.explanation.startswith("1 tracking phase-roles")
    assert "trackingAttackingMidfielder" in tracking.explanation
    assert TRACKING_ROLE_CODES == {
        "trackingCentreForward",
        "trackingAttackingMidfielder",
        "trackingWideMidfielder",
        "trackingWinger",
    }


def testAnalysisClassifiesFamilyChangeAndUnchangedSlots() -> None:
    analysis = _service(
        {
            "insideForward": {"dribbling": 4},
            "trackingWideMidfielder": {"work_rate": 5},
            "centreBack": {"marking": 4},
        }
    ).analysisBuild(
        _tactic(
            (
                _position("slot-wide", "AML", "insideForward"),
                _position("slot-dc", "DC", "centreBack"),
            ),
            (
                _position("slot-wide", "ML", "trackingWideMidfielder"),
                _position("slot-dc", "DC", "centreBack"),
            ),
        )
    )

    assert analysis is not None
    wide = next(slot for slot in analysis.slots if slot.slotId == "slot-wide")
    centre = next(slot for slot in analysis.slots if slot.slotId == "slot-dc")
    assert wide.transition.classification == "familyChange"
    assert wide.transition.ipFamily == "AMW"
    assert wide.transition.oopFamily == "MW"
    assert centre.transition.classification == "unchanged"
    family = next(item for item in analysis.observations if item.code == "familyChangeCount")
    assert family.explanation == "1 of 2 slots classifiable"


def testAnalysisDemandConcentrationUsesTopOverallAttributes() -> None:
    analysis = _service(
        {"insideForward": {"dribbling": 4, "finishing": 9, "pace": 6}}
    ).analysisBuild(_tactic((_position("slot-one", "AML", "insideForward"),)))

    assert analysis is not None
    concentration = next(
        item for item in analysis.observations if item.code == "demandConcentration"
    )
    assert concentration.explanation.startswith("Finishing 9")
    assert "Pace 6" in concentration.explanation
    assert "Dribbling 4" in concentration.explanation


def testAnalysisIsDeterministicForTheSameTacticAndPolicy() -> None:
    tactic = _tactic(
        (_position("slot-one", "AMC", "insideForward"),),
        (_position("slot-one", "MC", "winger"),),
    )
    weights = {"insideForward": {"dribbling": 4}, "winger": {"crossing": 3}}
    first = _service(weights).analysisBuild(tactic)
    second = _service(weights).analysisBuild(tactic)

    assert first == second


def testAnalysisModuleHasNoSquadOrUiDependencies() -> None:
    source = Path(tacticAnalysisModule.__file__).read_text(encoding="utf-8")
    for forbidden in ("SquadModel", "BestXi", "PySide", "QtGui", "QtWidgets", "genericRoleFit"):
        assert forbidden not in source
