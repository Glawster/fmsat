"""Phase-specific Structural Observation display for requirement 011."""

from fmsat.app.tacticAnalysisDisplay import tacticAnalysisDisplayBuild
from fmsat.core.tacticAnalysis import AttributeDemand, TacticAnalysis, TacticObservation


def _demand(
    name: str,
    ip: int | None,
    oop: int | None,
) -> AttributeDemand:
    return AttributeDemand(
        attribute=name.casefold().replace(" ", "_"),
        displayName=name,
        abbreviation="",
        overall=(ip or 0) + (oop or 0),
        inPossession=ip,
        outOfPossession=oop,
        contributingPhaseRoles=1,
        contributors=(),
        unavailableReason=None,
    )


def testCombinedDemandObservationIsReplacedByPhaseSpecificRows() -> None:
    analysis = TacticAnalysis(
        tacticName="Phase Test",
        scoringIdentity="test-policy",
        slotCount=0,
        weightCompletePhaseRoles=1,
        weightExpectedPhaseRoles=1,
        demandCoverageReason=None,
        slots=(),
        overallDemand=(
            _demand("Decisions", 56, 48),
            _demand("Off The Ball", 56, 14),
            _demand("Passing", 54, 12),
            _demand("Anticipation", 42, 48),
            _demand("Tackling", 34, 46),
        ),
        observations=(
            TacticObservation(
                code="demandConcentration",
                title="Highest combined attribute demands",
                explanation="Decisions 104, Anticipation 90, Tackling 80",
                attributes=(("Decisions", 104), ("Anticipation", 90), ("Tackling", 80)),
            ),
        ),
    )

    display = tacticAnalysisDisplayBuild(analysis)

    assert [(row.phase, row.finding) for row in display.observations] == [
        ("IP", "Highest attribute demands"),
        ("OOP", "Highest attribute demands"),
    ]
    assert display.observations[0].evidence == "Decisions 56, Off The Ball 56, Passing 54"
    assert display.observations[1].evidence == "Anticipation 48, Decisions 48, Tackling 46"
    assert all("combined" not in row.finding.casefold() for row in display.observations)
    assert all("104" not in row.evidence for row in display.observations)
