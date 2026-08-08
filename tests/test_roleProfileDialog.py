import yaml
from PySide6.QtWidgets import QDialogButtonBox, QLabel, QTableWidgetItem

from fmsat.app.colourPalette import cellHeader, cellHeaderText
from fmsat.app.roleProfileDialog import RoleProfileReviewDialog
from fmsat.core.config import AttributeDefinition
from fmsat.core.parser import RoleProfileEvidence, TacticalPhase, TacticVocabulary
from fmsat.core.roleKnowledge import RoleKnowledgeService


def testReviewDialogConfirmsDefinitionThroughService(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = RoleKnowledgeService(
        tmp_path,
        TacticVocabulary(),
        {"off_the_ball", "passing"},
    )
    evidence = RoleProfileEvidence(
        position="M (C)",
        roleName="Advanced Playmaker",
        phase=TacticalPhase.IN_POSSESSION,
        abbreviation="AP",
        keyAttributes=("off_the_ball", "passing"),
        displayedPlayerAttributes={"off_the_ball": 13, "passing": 14},
        playerInstructions=("takeMoreRisks",),
        sourceImport="role-profile.png",
        confidence=0.98,
    )
    dialog = RoleProfileReviewDialog(
        evidence,
        "MC",
        "advancedPlaymaker",
        service,
    )
    qtbot.addWidget(dialog)

    assert dialog.positionsEdit.text() == "MCR, MC, MCL, AMCR, AMC, AMCL"
    assert "Behaviours" in [label.text() for label in dialog.findChildren(QLabel)]

    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.savedPath is not None
    content = yaml.safe_load(dialog.savedPath.read_text(encoding="utf-8"))
    assert content["roleID"] == 19
    assert "displayedPlayerAttributes" not in content


def testReviewDialogAllowsMissingPhaseAndShowsWeightedAttributeGrid(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = RoleKnowledgeService(
        tmp_path / "roles",
        TacticVocabulary(),
        {"passing"},
    )
    evidence = RoleProfileEvidence(
        position="MC",
        roleName="Advanced Playmaker",
        keyAttributes=("passing",),
    )
    dialog = RoleProfileReviewDialog(
        evidence,
        "MC",
        "advancedPlaymaker",
        service,
        replaceExisting=True,
        attributeWeights={"passing": 4},
        attributeImportance={"passing": "topThree"},
        attributeDefinitions=(AttributeDefinition("passing", "Pas", 1),),
    )
    qtbot.addWidget(dialog)

    assert not dialog.phaseGroup.checkedButton()
    assert dialog.attributeTable.columnCount() == 4
    assert dialog.attributeTable.horizontalHeaderItem(2).text() == "Weight (0–5)"
    assert dialog.attributeTable.item(0, 0).text() == "Passing"
    assert dialog.attributeTable.item(0, 2).text() == "4"
    assert dialog.attributeTable.cellWidget(0, 3).currentText() == "Top three"
    assert "gridline-color" in dialog.attributeTable.styleSheet()
    assert cellHeader in dialog.attributeTable.styleSheet()
    assert cellHeaderText in dialog.attributeTable.styleSheet()

    dialog.bothPhasesRadio.setChecked(True)
    dialog.attributeTable.setItem(0, 2, QTableWidgetItem("5"))
    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert service.weightsLoad(19) == {"passing": 5}
    assert service.importanceLoad(19) == {"passing": "topThree"}
    content = yaml.safe_load(dialog.savedPath.read_text(encoding="utf-8"))
    assert content["inPossession"] is True
    assert content["outOfPossession"] is True
