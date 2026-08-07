import yaml
from PySide6.QtWidgets import QDialogButtonBox

from fmsat.app.roleProfileDialog import RoleProfileReviewDialog
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

    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.savedPath is not None
    content = yaml.safe_load(dialog.savedPath.read_text(encoding="utf-8"))
    assert content["id"] == "advancedPlaymaker"
    assert "displayedPlayerAttributes" not in content
