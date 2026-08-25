"""Regression tests for the 007C whole-team Best XI assignment policy."""

from types import SimpleNamespace

from fmsat.core.bestXi import BestXiAssignmentService


def _candidate(name: str, score: float, positions: str):
    return SimpleNamespace(
        name=name,
        positions=positions,
        score=f"{score:.1f}",
        available=True,
    )


def _role(code: str, abbreviation: str, phase: str, candidates: tuple[object, ...]):
    return SimpleNamespace(
        roleCode=code,
        displayName=code,
        abbreviation=abbreviation,
        phases=phase,
        candidates=candidates,
    )


def _slot(
    position: str,
    ipRole: str,
    oopRole: str,
    ipRoleCode: str | None = None,
    oopRoleCode: str | None = None,
):
    """Build display labels separately from the semantic identities Best XI consumes."""

    abbreviationCodes = {
        "SS": "secondStriker",
        "TAM": "trackingAttackingMidfielder",
        "IF": "insideForward",
        "TW": "trackingWinger",
        "1I": "oneIp",
        "1O": "oneOop",
        "2I": "twoIp",
        "2O": "twoOop",
        "WI": "wideIp",
        "WO": "wideOop",
        "RI": "roleIp",
        "RO": "roleOop",
    }
    return SimpleNamespace(
        position=position,
        ipRole=ipRole,
        oopRole=oopRole,
        ipRoleCode=ipRoleCode or abbreviationCodes.get(ipRole, ipRole),
        oopRoleCode=oopRoleCode or abbreviationCodes.get(oopRole, oopRole),
    )


def testBestXiMovesHempWideWhenFreigangCanCoverSecondStriker() -> None:
    """A slightly weaker local SS choice must be allowed to complete the whole XI."""

    hempCentral = _candidate("Hemp, Lauren", 81.0, "AM (L), ST (C)")
    freigangCentral = _candidate("Freigang, Laura", 77.0, "AM (C), ST (C)")
    hempWide = _candidate("Hemp, Lauren", 75.0, "AM (L), ST (C)")
    roles = (
        _role("secondStriker", "SS", "In Possession", (hempCentral, freigangCentral)),
        _role(
            "trackingAttackingMidfielder",
            "TAM",
            "Out Of Possession",
            (hempCentral, freigangCentral),
        ),
        _role("insideForward", "IF", "In Possession", (hempWide,)),
        _role("trackingWinger", "TW", "Out Of Possession", (hempWide,)),
    )
    slots = (_slot("AMC", "SS", "TAM"), _slot("AML", "IF", "TW"))

    result = BestXiAssignmentService().assignmentBuild(slots, roles)

    assert result.coveredSlots == 2
    assert result.selectionFor(0).playerName == "Freigang, Laura"
    assert result.selectionFor(1).playerName == "Hemp, Lauren"
    assert "scores higher locally" in result.selectionFor(0).evidence
    assert "stronger global XI" in result.selectionFor(0).evidence


def testBestXiCoverageOutranksAHighScoringPartialAssignment() -> None:
    """Two covered slots beat a locally stronger player that would leave one empty."""

    alphaOne = _candidate("Alpha", 99.0, "AM (C)")
    bravoOne = _candidate("Bravo", 60.0, "AM (C)")
    alphaTwo = _candidate("Alpha", 98.0, "AM (L)")
    roles = (
        _role("oneIp", "1I", "In Possession", (alphaOne, bravoOne)),
        _role("oneOop", "1O", "Out Of Possession", (alphaOne, bravoOne)),
        _role("twoIp", "2I", "In Possession", (alphaTwo,)),
        _role("twoOop", "2O", "Out Of Possession", (alphaTwo,)),
    )
    slots = (_slot("AMC", "1I", "1O"), _slot("AML", "2I", "2O"))

    result = BestXiAssignmentService().assignmentBuild(slots, roles)

    assert result.coveredSlots == 2
    assert result.selectionFor(0).playerName == "Bravo"
    assert result.selectionFor(1).playerName == "Alpha"


def testBestXiUsesStrongerWeakestAssignmentWhenTotalsTie() -> None:
    """Equal-total complete XIs prefer the one with the stronger weakest slot."""

    alphaOne = _candidate("Alpha", 90.0, "AM (C)")
    bravoOne = _candidate("Bravo", 80.0, "AM (C)")
    alphaTwo = _candidate("Alpha", 70.0, "AM (L)")
    bravoTwo = _candidate("Bravo", 60.0, "AM (L)")
    roles = (
        _role("oneIp", "1I", "In Possession", (alphaOne, bravoOne)),
        _role("oneOop", "1O", "Out Of Possession", (alphaOne, bravoOne)),
        _role("twoIp", "2I", "In Possession", (alphaTwo, bravoTwo)),
        _role("twoOop", "2O", "Out Of Possession", (alphaTwo, bravoTwo)),
    )
    slots = (_slot("AMC", "1I", "1O"), _slot("AML", "2I", "2O"))

    result = BestXiAssignmentService().assignmentBuild(slots, roles)

    assert result.totalScore == 150.0
    assert result.weakestScore == 70.0
    assert result.selectionFor(0).playerName == "Bravo"
    assert result.selectionFor(1).playerName == "Alpha"


def testBestXiUsesPositionFamiliarityAsLateTieBreak() -> None:
    """Familiarity breaks otherwise equal assignments without overriding role fit."""

    familiar = _candidate("Familiar", 75.0, "AM (L)")
    training = _candidate("Training", 75.0, "ST (C)")
    roles = (
        _role("wideIp", "WI", "In Possession", (training, familiar)),
        _role("wideOop", "WO", "Out Of Possession", (training, familiar)),
    )

    result = BestXiAssignmentService().assignmentBuild(
        (_slot("AML", "WI", "WO"),),
        roles,
    )

    assert result.selectionFor(0).playerName == "Familiar"
    assert result.selectionFor(0).familiar


def testBestXiIsDeterministicWhenEveryObjectiveIsEqual() -> None:
    """Stable alphabetical identity is the final tie-break."""

    alpha = _candidate("Alpha", 75.0, "AM (C)")
    bravo = _candidate("Bravo", 75.0, "AM (C)")
    roles = (
        _role("roleIp", "RI", "In Possession", (bravo, alpha)),
        _role("roleOop", "RO", "Out Of Possession", (bravo, alpha)),
    )

    result = BestXiAssignmentService().assignmentBuild(
        (_slot("AMC", "RI", "RO"),),
        roles,
    )

    assert result.selectionFor(0).playerName == "Alpha"


def testBestXiIgnoresUnresolvedPlaceholderDuplicateAbbreviations() -> None:
    """Role Editor placeholders must not wipe a calculable slot assignment."""

    player = _candidate("Alpha", 80.0, "AM (R)")
    roles = (
        _role("trackingWinger", "TW", "Out Of Possession", (player,)),
        SimpleNamespace(
            roleCode="unresolved:slot-11:OOP",
            displayName="Unknown AMR role",
            abbreviation="TW",
            phases="Out Of Possession",
            candidates=(),
            resolutionState="unknownRole",
        ),
        _role("insideForward", "IF", "In Possession", (player,)),
    )
    slots = (_slot("AMR", "IF", "TW"),)

    result = BestXiAssignmentService().assignmentBuild(slots, roles)

    assert result.coveredSlots == 1
    assert result.selectionFor(0).playerName == "Alpha"


def testBestXiResolvesSlotsByRoleCodeWhenAbbreviationIsUnknown() -> None:
    """Unknown abbreviation labels still assign when semantic roleCode is present."""

    player = _candidate("Alpha", 82.0, "ST (C)")
    roles = (
        _role("centreForward", "centreForward", "In Possession", (player,)),
        _role("trackingCentreForward", "TCF", "Out Of Possession", (player,)),
    )
    slot = SimpleNamespace(
        position="STC",
        ipRole="Unknown abbreviation",
        oopRole="TCF",
        ipRoleCode="centreForward",
        oopRoleCode="trackingCentreForward",
    )

    result = BestXiAssignmentService().assignmentBuild((slot,), roles)

    assert result.coveredSlots == 1
    assert result.selectionFor(0).playerName == "Alpha"


def testBestXiRefusesPartialPhaseEvidence() -> None:
    """One calculable phase must never stand in for a slot's missing phase role."""

    player = _candidate("Alpha", 82.0, "ST (C)")
    roles = (_role("trackingCentreForward", "TCF", "Out Of Possession", (player,)),)
    slot = SimpleNamespace(
        position="STC",
        ipRole="Complete Forward",
        oopRole="TCF",
        ipRoleCode="completeForward",
        oopRoleCode="trackingCentreForward",
    )

    result = BestXiAssignmentService().assignmentBuild((slot,), roles)

    assert result.coveredSlots == 0
    assert not result.evidenceAvailable
