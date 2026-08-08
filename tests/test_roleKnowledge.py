from pathlib import Path

import pytest
import yaml

from fmsat.core.parser import (
    FormationSlot,
    RoleProfileEvidence,
    TacticalPhase,
    TacticVocabulary,
)
from fmsat.core.roleKnowledge import (
    RoleKnowledgeError,
    RoleKnowledgeService,
    roleKnowledgeGaps,
)


def _advancedPlaymakerEvidence() -> RoleProfileEvidence:
    return RoleProfileEvidence(
        position="M (C)",
        roleName="Advanced Playmaker",
        phase=TacticalPhase.IN_POSSESSION,
        abbreviation="AP",
        behaviours=("findsSpaceBetweenLines", "expressive"),
        description="A creative role operating between midfield and defence.",
        keyAttributes=("offTheBall", "passing", "vision", "decisions"),
        playerInstructions=("takeMoreRisks",),
        displayedPlayerAttributes={
            "offTheBall": 13,
            "passing": 14,
            "vision": 14,
            "decisions": 13,
        },
        suitabilityStars=3.5,
        sourceImport="fm26-mc-advancedPlaymaker.png",
    )


def _serviceCreate(directory: Path) -> RoleKnowledgeService:
    return RoleKnowledgeService(
        directory,
        TacticVocabulary(),
        {"offTheBall", "passing", "vision", "decisions"},
    )


def testKnowledgeGapsDeduplicateRoleAndPositionAcrossTacticSlots() -> None:
    slots = (
        FormationSlot("mc-1", TacticalPhase.FORMATION, "MC", "advancedPlaymaker", None, 0.5, 0.5),
        FormationSlot(
            "mc-2",
            TacticalPhase.IN_POSSESSION,
            "MC",
            "advancedPlaymaker",
            None,
            0.5,
            0.4,
        ),
        FormationSlot("aml-1", TacticalPhase.FORMATION, "AML", "insideForward", None, 0.2, 0.3),
    )

    gaps = roleKnowledgeGaps(slots, {"insideForward"})

    assert len(gaps) == 1
    assert gaps[0].role == "advancedPlaymaker"
    assert gaps[0].position == "MC"
    assert gaps[0].slotIds == ("mc-1", "mc-2")


def testEvidenceMustMatchExpectedRoleAndPosition(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path)
    evidence = _advancedPlaymakerEvidence()

    with pytest.raises(RoleKnowledgeError, match="Expected position AMC"):
        service.evidenceVerify(evidence, "AMC", "advancedPlaymaker")

    with pytest.raises(RoleKnowledgeError, match="Expected role insideForward"):
        service.evidenceVerify(evidence, "MC", "insideForward")


def testEvidenceMustOnlyReferenceKnownAttributes(tmp_path: Path) -> None:
    service = RoleKnowledgeService(tmp_path, TacticVocabulary(), {"passing"})

    with pytest.raises(RoleKnowledgeError, match="Unknown key attributes"):
        service.evidenceVerify(_advancedPlaymakerEvidence(), "MC", "advancedPlaymaker")


def testVerifiedEvidenceCanAdoptANewDetectedRole(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path)
    evidence = RoleProfileEvidence(
        position="D (C)",
        roleName="Ball-Playing Centre-Back.",
        phase=TacticalPhase.IN_POSSESSION,
        keyAttributes=("passing",),
    )

    draft = service.evidenceVerify(
        evidence,
        "DC",
        "ballPlayingDefender",
        adoptDetectedRole=True,
    )

    assert draft.id == "ballPlayingCentreBack"
    assert draft.displayName == "Ball-Playing Centre-Back."
    assert draft.phase is TacticalPhase.IN_POSSESSION


def testConfirmedDefinitionExcludesPlayerValuesStarsAndWeights(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path)
    draft = service.evidenceVerify(_advancedPlaymakerEvidence(), "MC", "advancedPlaymaker")

    path = service.definitionConfirm(draft)
    content = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert content["id"] == "advancedPlaymaker"
    assert content["positions"] == ["MC"]
    assert content["inPossession"] is True
    assert content["outOfPossession"] is False
    assert content["keyAttributes"] == ["offTheBall", "passing", "vision", "decisions"]
    assert content["provenance"]["reviewState"] == "confirmed"
    assert "displayedPlayerAttributes" not in content
    assert "suitabilityStars" not in content
    assert "weights" not in content


def testRoleAbbreviationIsStoredInUppercase(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path)
    evidence = RoleProfileEvidence(
        position="ST (C)",
        roleName="Channel Forward",
        phase=TacticalPhase.IN_POSSESSION,
        abbreviation="ChF",
        keyAttributes=("passing",),
    )

    draft = service.evidenceVerify(evidence, "STC", "channelForward")
    path = service.definitionConfirm(draft)
    content = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert draft.abbreviations == ("CHF",)
    assert content["abbreviations"] == ["CHF"]


def testExistingRoleAbbreviationsAreNormalizedWhenReplaced(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path)
    path = tmp_path / "channelForward.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "id": "channelForward",
                "displayName": "Channel Forward",
                "inPossession": True,
                "abbreviations": ["ChF"],
            }
        ),
        encoding="utf-8",
    )
    evidence = RoleProfileEvidence(
        position="ST (C)",
        roleName="Channel Forward",
        phase=TacticalPhase.IN_POSSESSION,
        abbreviation="CHF",
        keyAttributes=("passing",),
    )

    draft = service.evidenceVerify(evidence, "STC", "channelForward")
    service.definitionConfirm(draft, replace=True)
    content = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert content["abbreviations"] == ["CHF"]


def testExistingDefinitionRequiresExplicitReplacement(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path)
    draft = service.evidenceVerify(_advancedPlaymakerEvidence(), "MC", "advancedPlaymaker")
    service.definitionConfirm(draft)

    with pytest.raises(RoleKnowledgeError, match="already contains inPossession"):
        service.definitionConfirm(draft)


def testDefinitionExistsOnlyAfterConfirmation(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path)

    assert service.definitionExists("advancedPlaymaker") is False

    draft = service.evidenceVerify(_advancedPlaymakerEvidence(), "MC", "advancedPlaymaker")
    service.definitionConfirm(draft)

    assert service.definitionExists("advancedPlaymaker") is True


def testPossessionPhaseDefinitionsForOneRoleCanCoexist(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path)
    inPossession = _advancedPlaymakerEvidence()
    outOfPossession = RoleProfileEvidence(
        position=inPossession.position,
        roleName=inPossession.roleName,
        phase=TacticalPhase.OUT_OF_POSSESSION,
        abbreviation=inPossession.abbreviation,
        keyAttributes=inPossession.keyAttributes,
    )

    first = service.definitionConfirm(
        service.evidenceVerify(inPossession, "MC", "advancedPlaymaker")
    )
    second = service.definitionConfirm(
        service.evidenceVerify(outOfPossession, "MC", "advancedPlaymaker")
    )

    assert first.name == "advancedPlaymaker.yaml"
    assert second == first
    assert service.definitionExists("advancedPlaymaker", TacticalPhase.IN_POSSESSION)
    assert service.definitionExists("advancedPlaymaker", TacticalPhase.OUT_OF_POSSESSION)
    content = yaml.safe_load(first.read_text(encoding="utf-8"))
    assert content["inPossession"] is True
    assert content["outOfPossession"] is True
