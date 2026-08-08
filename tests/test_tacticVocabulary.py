from pathlib import Path

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


def testRoleAbbreviationNormalizesToStableNamedIdentity() -> None:
    vocabulary = TacticVocabulary()

    assert vocabulary.roleNormalize("AP").value == "advancedPlaymaker"
    assert vocabulary.roleNormalize("Advanced Playmaker").value == "advancedPlaymaker"
    assert vocabulary.roles["channelForward"].abbreviations == ("CHF",)


def testUnknownVocabularyDoesNotInventMeaning() -> None:
    value = TacticVocabulary().roleNormalize("Raumdeuter-ish")

    assert value.value is None
    assert value.observedText == "Raumdeuter-ish"
    assert value.resolved is False


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
            position="MC",
            roleName="Advanced Playmaker",
            displayedPlayerAttributes={"passing": 21},
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
