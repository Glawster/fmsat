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


def testPackagedWeightsAreUsedWhenNoUserOverrideExists(tmp_path: Path) -> None:
    """A complete packaged role policy should make known roles assessable by default."""

    service = RoleKnowledgeService(
        tmp_path,
        TacticVocabulary(),
        {"passing", "vision"},
        {"advancedPlaymaker": {"passing": 5, "vision": 4}},
    )

    assert service.weightsLoad("advancedPlaymaker") == {"passing": 5, "vision": 4}
    assert service.weightsLoad(19) == {"passing": 5, "vision": 4}


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
    vocabulary = TacticVocabulary()
    expectedRoleID = max(role.roleID for role in vocabulary.roles.values()) + 1
    service = RoleKnowledgeService(
        tmp_path,
        vocabulary,
        {"offTheBall", "passing", "vision", "decisions"},
    )
    evidence = RoleProfileEvidence(
        position="D (C)",
        roleName="Libero.",
        phase=TacticalPhase.IN_POSSESSION,
        keyAttributes=("passing",),
    )

    draft = service.evidenceVerify(
        evidence,
        "DC",
        "ballPlayingCentreBack",
        adoptDetectedRole=True,
    )

    assert draft.roleID == expectedRoleID
    assert draft.displayName == "Libero."
    assert draft.phase is TacticalPhase.IN_POSSESSION
    path = service.definitionConfirm(draft)
    assert path.name == f"role-{expectedRoleID:03d}.yaml"
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["roleCode"] == "libero"


def testLegacyTextNamedDefinitionRemainsRecognized(tmp_path: Path) -> None:
    (tmp_path / "centreForward.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "centreForward",
                "displayName": "Centre Forward",
                "inPossession": True,
            }
        ),
        encoding="utf-8",
    )
    service = _serviceCreate(tmp_path)

    assert service.definitionExists("centreForward")
    assert service.definitionExists("centreForward", TacticalPhase.IN_POSSESSION)


def testLegacyNumericCollisionUsesConfirmedRoleNameNotNumericId(tmp_path: Path) -> None:
    """Old TAM evidence remains TAM even if its historical ID now belongs to Free Role."""

    (tmp_path / "role-020.yaml").write_text(
        yaml.safe_dump(
            {
                "roleID": 20,
                "displayName": "Tracking Attacking Midfielder",
                "abbreviations": ["TAM"],
                "positions": ["AMC"],
                "outOfPossession": True,
            }
        ),
        encoding="utf-8",
    )
    service = _serviceCreate(tmp_path)

    definitions = service.definitionsList()

    assert len(definitions) == 1
    assert definitions[0].roleCode == "trackingAttackingMidfielder"
    assert definitions[0].roleID == 20
    service.vocabulary.capturedRolesAdd(definitions)
    assert service.vocabulary.roleNormalize("TAM").value == "trackingAttackingMidfielder"
    assert service.vocabulary.roleNormalize("FR").value == "freeRole"


def testConfirmedDefinitionExcludesPlayerValuesStarsAndWeights(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path)
    draft = service.evidenceVerify(_advancedPlaymakerEvidence(), "MC", "advancedPlaymaker")

    path = service.definitionConfirm(draft)
    content = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert content["roleCode"] == "advancedPlaymaker"
    assert content["roleID"] == 19
    assert "id" not in content
    assert content["positions"] == ["MCR", "MC", "MCL", "AMCR", "AMC", "AMCL"]
    assert content["inPossession"] is True
    assert content["outOfPossession"] is False
    assert content["keyAttributes"] == ["offTheBall", "passing", "vision", "decisions"]
    assert content["provenance"]["reviewState"] == "confirmed"
    assert "displayedPlayerAttributes" not in content
    assert "suitabilityStars" not in content
    assert "weights" not in content


def testKnownRoleDefinitionRetainsAllSupportedPositionsAndIndicators(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path)
    evidence = RoleProfileEvidence(
        position="AM (L)",
        roleName="Inside Forward",
        phase=TacticalPhase.IN_POSSESSION,
        abbreviation="IF",
        behaviours=("movesInside", "goalThreat"),
        keyAttributes=("offTheBall",),
    )

    draft = service.evidenceVerify(
        evidence,
        "AML",
        "insideForward",
        supportedPositions=("AML", "AMR"),
    )
    path = service.definitionConfirm(draft)
    content = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert draft.positions == ("AML", "AMR")
    assert content["positions"] == ["AML", "AMR"]
    assert content["behaviours"] == ["movesInside", "goalThreat"]


def testSupportedPositionsRejectUnknownCode(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path)
    evidence = RoleProfileEvidence(
        position="AM (L)",
        roleName="Inside Forward",
        phase=TacticalPhase.IN_POSSESSION,
        keyAttributes=("offTheBall",),
    )

    with pytest.raises(RoleKnowledgeError, match="Unknown supported position: AMT"):
        service.evidenceVerify(
            evidence,
            "AML",
            "insideForward",
            supportedPositions=("AML", "AMT"),
        )


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
    migratedPath = service.definitionConfirm(draft, replace=True)
    content = yaml.safe_load(migratedPath.read_text(encoding="utf-8"))

    assert content["roleCode"] == "channelForward"
    assert content["abbreviations"] == ["CHF"]
    assert content["roleID"] == 17
    assert "id" not in content
    assert migratedPath.name == "channelForward.yaml"


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

    assert first.name == "role-019.yaml"
    assert second == first
    assert service.definitionExists("advancedPlaymaker", TacticalPhase.IN_POSSESSION)
    assert service.definitionExists("advancedPlaymaker", TacticalPhase.OUT_OF_POSSESSION)
    content = yaml.safe_load(first.read_text(encoding="utf-8"))
    assert content["roleCode"] == "advancedPlaymaker"
    assert content["inPossession"] is True
    assert content["outOfPossession"] is True


def testAssessmentWeightsAreStoredSeparatelyFromRoleFacts(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path / "roles")
    draft = service.evidenceVerify(_advancedPlaymakerEvidence(), "MC", "advancedPlaymaker")
    rolePath = service.definitionConfirm(draft)
    weightsPath = service.weightsConfirm(
        "advancedPlaymaker",
        {"passing": 5, "vision": 4},
        {"passing": "topThree", "vision": "important"},
    )

    assert weightsPath is not None
    assert weightsPath.name == "advancedPlaymaker.yaml"
    assert weightsPath.parent.name == "requirements"
    assert service.weightsLoad("advancedPlaymaker") == {"passing": 5, "vision": 4}
    assert service.importanceLoad("advancedPlaymaker") == {
        "passing": "topThree",
        "vision": "important",
    }
    assert "attributeWeights" not in yaml.safe_load(rolePath.read_text(encoding="utf-8"))


def testAssessmentRejectsMoreThanThreeTopAttributes(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path / "roles")

    with pytest.raises(RoleKnowledgeError, match="at most three"):
        service.weightsConfirm(
            "advancedPlaymaker",
            {},
            {
                "offTheBall": "topThree",
                "passing": "topThree",
                "vision": "topThree",
                "decisions": "topThree",
            },
        )


def testDefinitionDeleteRemovesRoleAndRequirements(tmp_path: Path) -> None:
    service = _serviceCreate(tmp_path / "roles")
    draft = service.evidenceVerify(_advancedPlaymakerEvidence(), "MC", "advancedPlaymaker")
    rolePath = service.definitionConfirm(draft)
    weightsPath = service.weightsConfirm(
        "advancedPlaymaker",
        {"passing": 5},
        {"passing": "topThree"},
    )

    deletedPaths = service.definitionDelete(19)

    assert rolePath in deletedPaths
    assert weightsPath in deletedPaths
    assert not rolePath.exists()
    assert weightsPath is not None
    assert not weightsPath.exists()
