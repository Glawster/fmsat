from pathlib import Path
from types import SimpleNamespace

import pytest

from fmsat.core.config import ConfigurationError
from fmsat.core.parser import RoleProfileEvidence, TacticVocabulary


def testBundledVocabularyContainsRequiredTacticalContract() -> None:
    vocabulary = TacticVocabulary()

    assert vocabulary.version == 1
    assert set(vocabulary.positions.values()) == {
        "GK",
        "DR",
        "DCR",
        "DC",
        "DCL",
        "DL",
        "WBR",
        "DMCR",
        "DM",
        "DMCL",
        "WBL",
        "MR",
        "MCR",
        "MC",
        "MCL",
        "ML",
        "AMR",
        "AMCR",
        "AMC",
        "AMCL",
        "AML",
        "STCR",
        "STC",
        "STCL",
    }
    assert vocabulary.roles["insideForward"].positions == ("AMR", "AML")
    assert "tempo" in vocabulary.instructions["inPossession"]
    assert "defensiveLine" in vocabulary.instructions["outOfPossession"]


def testVocabularyNormalizesAliasesAndPreservesObservedText() -> None:
    vocabulary = TacticVocabulary()

    role = vocabulary.roleNormalize("  Inside-Forward ")
    position = vocabulary.positionNormalize("left attacking midfielder")
    duty = vocabulary.dutyNormalize("Att")
    instruction = vocabulary.instructionNormalize("inPossession", "tempo", "Much Higher")

    assert (role.value, role.observedText) == ("insideForward", "  Inside-Forward ")
    assert position.value == "AML"
    assert duty.value == "ATTACK"
    assert instruction.value == "much higher"
    assert vocabulary.positionNormalize("ST (C)").value == "STC"
    assert vocabulary.positionNormalize("AM ( C )").value == "AMC"
    assert vocabulary.positionNormalize("AM(C)").value == "AMC"
    assert vocabulary.positionNormalize("AM (L)").value == "AML"
    assert vocabulary.roleIndicatorNormalize("Moves Inside").value == "movesInside"


def testInstructionVocabularyNormalizesFm26DisplayedAliases() -> None:
    vocabulary = TacticVocabulary()

    assert (
        vocabulary.instructionNormalize(
            "inPossession", "attackingTransition", "Counter-Attack"
        ).value
        == "counter"
    )
    assert (
        vocabulary.instructionNormalize("outOfPossession", "tackling", "Standard").value
        == "balanced"
    )
    assert (
        vocabulary.instructionNormalize(
            "outOfPossession", "shortGoalkeeperDistribution", "No"
        ).value
        == "false"
    )


def testInstructionVocabularyNormalizesCurrentFm26DisplayedValues() -> None:
    vocabulary = TacticVocabulary()

    assert (
        vocabulary.instructionNormalize("inPossession", "creativeFreedom", "More Express..").value
        == "be more expressive"
    )
    assert (
        vocabulary.instructionNormalize("inPossession", "supportingRuns", "Both Flanks").value
        == "both flanks"
    )
    assert (
        vocabulary.instructionNormalize("inPossession", "progressThrough", "Both Flanks").value
        == "both flanks"
    )
    assert (
        vocabulary.instructionNormalize("inPossession", "patience", "Standard").value == "standard"
    )
    assert (
        vocabulary.instructionNormalize("inPossession", "patience", "Work Ball Into..").value
        == "work ball into box"
    )
    assert (
        vocabulary.instructionNormalize("inPossession", "shotsFromDistance", "Discourage").value
        == "discourage"
    )


def testInstructionVocabularyNormalizesUniqueDisplayedEllipsis() -> None:
    vocabulary = TacticVocabulary()

    assert (
        vocabulary.instructionNormalize(
            "inPossession", "playForSetPieces", "Keep Ball in Pl..."
        ).value
        == "true"
    )
    assert (
        vocabulary.instructionNormalize("inPossession", "passReception", "Pass Into Spa…").value
        == "into space"
    )
    assert (
        vocabulary.instructionNormalize(
            "inPossession", "goalkeeperDistributionSpeed", "Distribute Qui..."
        ).value
        == "distribute quickly"
    )
    assert (
        vocabulary.instructionNormalize("inPossession", "crossingStyle", "Whipped Cro").value
        == "whipped"
    )
    assert (
        vocabulary.instructionNormalize(
            "inPossession", "goalkeeperDistributionSpeed", "Distribute Qui"
        ).value
        == "distribute quickly"
    )


def testRoleAbbreviationNormalizesToStableNamedIdentity() -> None:
    vocabulary = TacticVocabulary()

    assert vocabulary.roleNormalize("AP").value == "advancedPlaymaker"
    assert vocabulary.roleNormalize("Advanced Playmaker").value == "advancedPlaymaker"
    assert vocabulary.roles["channelForward"].abbreviations == ("CHF",)
    assert vocabulary.roleNormalize("BGK").value == "ballPlayingGoalkeeper"
    assert vocabulary.roleNormalize("BCB").value == "ballPlayingCentreBack"
    assert vocabulary.roleNormalize("Ball-Playing Defender").value is None
    assert vocabulary.roleNormalize("CFD").value == "centreForward"
    assert vocabulary.roleNormalize("Complete Forward").value is None
    assert vocabulary.roles["centreForward"].roleID == 15


def testConfiguredRoleProfileAbbreviationsAreCanonicalTacticalRoles() -> None:
    """Roles exposed by OCR role definitions must never require tactic redefinition."""

    vocabulary = TacticVocabulary()
    expected = {
        "FR": "freeRole",
        "SS": "secondStriker",
        "CHM": "channelMidfielder",
        "PW": "playmakingWinger",
        "WF": "wideForward",
        "IW": "insideWinger",
        "DLF": "deepLyingForward",
        "P": "poacher",
        "F9": "falseNine",
        "HB": "halfBack",
        "DDM": "droppingDefensiveMidfielder",
    }

    for abbreviation, canonical in expected.items():
        assert vocabulary.roleNormalize(abbreviation).value == canonical


def testConfirmedOcrRoleDefinitionsAreAuditedAgainstTacticalVocabulary() -> None:
    vocabulary = TacticVocabulary()
    definitions = (
        SimpleNamespace(displayName="Half-Back", abbreviations=("HB",)),
        SimpleNamespace(displayName="Dropping Defensive Midfielder", abbreviations=("DDM",)),
        SimpleNamespace(displayName="Unmapped Test Role", abbreviations=("UTR",)),
    )

    assert vocabulary.canonicalRoleDefinitionGaps(definitions) == ("Unmapped Test Role",)


def testUnknownVocabularyDoesNotInventMeaning() -> None:
    value = TacticVocabulary().roleNormalize("Raumdeuter-ish")

    assert value.value is None
    assert value.observedText == "Raumdeuter-ish"
    assert value.resolved is False


def testCapturedRoleDefinitionExtendsLiveOcrVocabularyBySemanticCode() -> None:
    vocabulary = TacticVocabulary()
    vocabulary.capturedRolesAdd(
        (
            SimpleNamespace(
                roleCode="advancedWingBack",
                displayName="Advanced Wing-Back",
                abbreviations=("AWB",),
                positions=("WBL", "WBR"),
            ),
        )
    )

    value = vocabulary.roleNormalize("AWB")

    assert value.value == "advancedWingBack"
    assert value.observedText == "AWB"


def testLegacyNumericCollisionDoesNotChangeCapturedRoleIdentity() -> None:
    """A stale numeric ID cannot turn TAM into whichever role later received that ID."""

    vocabulary = TacticVocabulary()
    vocabulary.capturedRolesAdd(
        (
            SimpleNamespace(
                roleID=20,
                roleCode="trackingAttackingMidfielder",
                displayName="Tracking Attacking Midfielder",
                abbreviations=("TAM",),
                positions=("AMC",),
            ),
        )
    )

    assert vocabulary.roleNormalize("TAM").value == "trackingAttackingMidfielder"
    assert (
        vocabulary.roleNormalize("Tracking Attacking Midfielder").value
        == "trackingAttackingMidfielder"
    )
    assert vocabulary.roleNormalize("FR").value == "freeRole"


def testStaleCapturedRoleCodeDoesNotOverrideCapturedAliases() -> None:
    """Captured TAM evidence must win if an old migration incorrectly stored freeRole."""

    vocabulary = TacticVocabulary()
    vocabulary.capturedRolesAdd(
        (
            SimpleNamespace(
                roleID=20,
                roleCode="freeRole",
                displayName="Dropping Defensive Midfielder",
                abbreviations=("TAM",),
                positions=("AMC",),
            ),
        )
    )

    assert vocabulary.roleNormalize("TAM").value == "trackingAttackingMidfielder"
    assert (
        vocabulary.roleNormalize("Tracking Attacking Midfielder").value
        == "trackingAttackingMidfielder"
    )
    assert vocabulary.roleNormalize("FR").value == "freeRole"


def testCapturedRoleAlreadyCanonicalDoesNotDuplicateAlias() -> None:
    """Legacy confirmed roles must defer to a role now supplied canonically."""

    vocabulary = TacticVocabulary()
    vocabulary.capturedRolesAdd(
        (
            SimpleNamespace(
                roleID=20,
                roleCode="freeRole",
                displayName="Free Role",
                abbreviations=("FR",),
                positions=("AMC",),
            ),
        )
    )

    assert vocabulary.roleNormalize("Free Role").value == "freeRole"
    assert vocabulary.roleNormalize("FR").value == "freeRole"


def testRoleCodeIsDerivedFromRoleNameNotNumericSequence() -> None:
    assert (
        TacticVocabulary.roleCodeCreate("Tracking Attacking Midfielder", "TAM")
        == "trackingAttackingMidfielder"
    )


def testRoleProfileEvidenceSeparatesKeyAttributesFromPlayerValues() -> None:
    evidence = RoleProfileEvidence(
        position="MC",
        roleName="Advanced Playmaker",
        abbreviation="AP",
        behaviours=("findsSpaceBetweenLines", "expressive"),
        keyAttributes=(
            "offTheBall",
            "passing",
            "vision",
            "decisions",
            "firstTouch",
            "technique",
            "teamwork",
            "composure",
        ),
        playerInstructions=("takeMoreRisks",),
        displayedPlayerAttributes={
            "offTheBall": 13,
            "passing": 14,
            "vision": 14,
            "decisions": 13,
            "firstTouch": 14,
            "technique": 14,
            "teamwork": 12,
            "composure": 14,
        },
        suitabilityStars=3.5,
        sourceImport="fm26-role-profile.png",
    )

    assert evidence.keyAttributes[0] == "offTheBall"
    assert evidence.playerValuesForKeyAttributes()["passing"] == 14
    assert not hasattr(evidence, "weights")


def testRoleProfileEvidenceRejectsImpossibleDisplayedAttribute() -> None:
    with pytest.raises(ValueError, match="between 1 and 20"):
        RoleProfileEvidence(
            position="MC", roleName="Advanced Playmaker", displayedPlayerAttributes={"passing": 21}
        )


def testVocabularyRejectsUnknownRolePosition(tmp_path: Path) -> None:
    path = tmp_path / "tacticalVocabulary.yaml"
    path.write_text(
        """
version: 1
duties: {DEFEND: [defend]}
positions: {GK: [goalkeeper]}
roles:
  SK:
    roleID: 1
    displayName: Sweeper Keeper
    abbreviations: [SK]
    positions: [MISSING]
    duties: [DEFEND]
instructions: {}
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="unknown positions.*MISSING"):
        TacticVocabulary(path)
