import yaml
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialogButtonBox, QLabel, QMessageBox, QPushButton, QTableWidgetItem

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
    assert dialog.attributeTable.columnCount() == 3
    assert dialog.attributeTable.horizontalHeaderItem(1).text() == "Weight (0–10)"
    assert dialog.attributeTable.item(0, 0).text() == "Passing"
    assert dialog.attributeTable.item(0, 1).text() == "4"
    assert dialog.attributeTable.cellWidget(0, 2).currentText() == "Top three"
    assert "gridline-color" in dialog.attributeTable.styleSheet()
    assert cellHeader in dialog.attributeTable.styleSheet()
    assert cellHeaderText in dialog.attributeTable.styleSheet()

    dialog.bothPhasesRadio.setChecked(True)
    dialog.attributeTable.setItem(0, 1, QTableWidgetItem("5"))
    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert service.weightsLoad(19) == {"passing": 5}
    assert service.importanceLoad(19) == {"passing": "topThree"}
    content = yaml.safe_load(dialog.savedPath.read_text(encoding="utf-8"))
    assert content["inPossession"] is True
    assert content["outOfPossession"] is True


def testReviewDialogAddsAttributeRowAndMarksFirstThreeTopThree(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = RoleKnowledgeService(
        tmp_path,
        TacticVocabulary(),
        {"passing", "off_the_ball", "vision"},
    )
    evidence = RoleProfileEvidence(
        position="MC",
        roleName="Advanced Playmaker",
        phase=TacticalPhase.IN_POSSESSION,
        keyAttributes=("passing", "off_the_ball", "vision"),
        displayedPlayerAttributes={"passing": 12, "off_the_ball": 13, "vision": 14},
    )
    dialog = RoleProfileReviewDialog(
        evidence,
        "MC",
        "advancedPlaymaker",
        service,
    )
    qtbot.addWidget(dialog)

    assert dialog.attributeTable.rowCount() == 3
    assert dialog.attributeTable.cellWidget(0, 2).currentText() == "Top three"
    assert dialog.attributeTable.cellWidget(1, 2).currentText() == "Top three"
    assert dialog.attributeTable.cellWidget(2, 2).currentText() == "Top three"

    addButton = dialog.findChild(QPushButton, "addAttributeButton")
    assert addButton is not None
    addButton.click()

    assert dialog.attributeTable.rowCount() == 4
    assert dialog.attributeTable.item(3, 0).text() == ""
    assert dialog.attributeTable.cellWidget(3, 2).currentText() == "Unassigned"


def testReviewDialogDeletesSelectedAttributeRow(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = RoleKnowledgeService(
        tmp_path,
        TacticVocabulary(),
        {"passing", "off_the_ball", "vision"},
    )
    evidence = RoleProfileEvidence(
        position="MC",
        roleName="Advanced Playmaker",
        phase=TacticalPhase.IN_POSSESSION,
        keyAttributes=("passing", "off_the_ball", "vision"),
        displayedPlayerAttributes={"passing": 12, "off_the_ball": 13, "vision": 14},
    )
    dialog = RoleProfileReviewDialog(
        evidence,
        "MC",
        "advancedPlaymaker",
        service,
    )
    qtbot.addWidget(dialog)

    deleteButton = dialog.findChild(QPushButton, "deleteAttributeButton")
    assert deleteButton is not None
    assert not deleteButton.isEnabled()

    dialog.attributeTable.setCurrentCell(1, 0)

    assert deleteButton.isEnabled()
    removedName = dialog.attributeTable.item(1, 0).text()
    deleteButton.click()

    assert dialog.attributeTable.rowCount() == 2
    remainingNames = [dialog.attributeTable.item(row, 0).text() for row in range(2)]
    assert removedName == "Off The Ball"
    assert remainingNames == ["Passing", "Vision"]


def testReviewDialogReordersAttributesWhenImportanceChanges(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = RoleKnowledgeService(
        tmp_path,
        TacticVocabulary(),
        {"first_touch", "passing", "technique", "composure"},
    )
    evidence = RoleProfileEvidence(
        position="DM",
        roleName="Deep-Lying Playmaker",
        phase=TacticalPhase.IN_POSSESSION,
        keyAttributes=("first_touch", "passing", "technique", "composure"),
        displayedPlayerAttributes={
            "first_touch": 16,
            "passing": 17,
            "technique": 15,
            "composure": 15,
        },
    )
    dialog = RoleProfileReviewDialog(
        evidence,
        "DM",
        "deepLyingPlaymaker",
        service,
        attributeDefinitions=(
            AttributeDefinition("first_touch", "Fir", 1),
            AttributeDefinition("passing", "Pas", 2),
            AttributeDefinition("technique", "Tec", 3),
            AttributeDefinition("composure", "Com", 4),
        ),
    )
    qtbot.addWidget(dialog)

    def rowIndex(name: str) -> int:
        for row in range(dialog.attributeTable.rowCount()):
            if dialog.attributeTable.item(row, 0).text() == name:
                return row
        raise AssertionError(f"Attribute row not found: {name}")

    dialog.attributeTable.cellWidget(rowIndex("Passing"), 2).setCurrentText("Important")

    assert [dialog.attributeTable.item(row, 0).text() for row in range(4)] == [
        "First Touch",
        "Technique",
        "Passing",
        "Composure",
    ]
    assert [dialog.attributeTable.cellWidget(row, 2).currentText() for row in range(4)] == [
        "Top three",
        "Top three",
        "Important",
        "Unassigned",
    ]

    dialog.attributeTable.cellWidget(rowIndex("Composure"), 2).setCurrentText("Top three")

    assert [dialog.attributeTable.item(row, 0).text() for row in range(4)] == [
        "First Touch",
        "Technique",
        "Composure",
        "Passing",
    ]
    assert [dialog.attributeTable.cellWidget(row, 2).currentText() for row in range(4)] == [
        "Top three",
        "Top three",
        "Top three",
        "Important",
    ]


def testReviewDialogMoveArrowPromotesRowIntoTopThree(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = RoleKnowledgeService(
        tmp_path,
        TacticVocabulary(),
        {"first_touch", "passing", "technique", "composure"},
    )
    evidence = RoleProfileEvidence(
        position="DM",
        roleName="Deep-Lying Playmaker",
        phase=TacticalPhase.IN_POSSESSION,
        keyAttributes=("first_touch", "passing", "technique", "composure"),
    )
    dialog = RoleProfileReviewDialog(
        evidence,
        "DM",
        "deepLyingPlaymaker",
        service,
        attributeDefinitions=(
            AttributeDefinition("first_touch", "Fir", 1),
            AttributeDefinition("passing", "Pas", 2),
            AttributeDefinition("technique", "Tec", 3),
            AttributeDefinition("composure", "Com", 4),
        ),
    )
    qtbot.addWidget(dialog)

    dialog.attributeTable.setCurrentCell(3, 0)
    moveUp = dialog.findChild(QPushButton, "moveAttributeUpButton")

    assert moveUp is not None
    assert moveUp.isEnabled()

    qtbot.mouseClick(moveUp, Qt.MouseButton.LeftButton)

    assert [dialog.attributeTable.item(row, 0).text() for row in range(4)] == [
        "First Touch",
        "Passing",
        "Composure",
        "Technique",
    ]
    assert [dialog.attributeTable.cellWidget(row, 2).currentText() for row in range(4)] == [
        "Top three",
        "Top three",
        "Top three",
        "Important",
    ]


def testReviewDialogDropdownPromotionDemotesLastExistingTopThree(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """The dropdown promotes a fourth attribute and makes deterministic room for it."""

    service = RoleKnowledgeService(
        tmp_path,
        TacticVocabulary(),
        {"first_touch", "passing", "technique", "work_rate"},
    )
    evidence = RoleProfileEvidence(
        position="DM",
        roleName="Deep-Lying Playmaker",
        phase=TacticalPhase.IN_POSSESSION,
        keyAttributes=("first_touch", "passing", "technique", "work_rate"),
    )
    dialog = RoleProfileReviewDialog(
        evidence,
        "DM",
        "deepLyingPlaymaker",
        service,
    )
    qtbot.addWidget(dialog)

    dialog.attributeTable.cellWidget(3, 2).setCurrentText("Top three")

    assert [dialog.attributeTable.item(row, 0).text() for row in range(4)] == [
        "First Touch",
        "Passing",
        "Work Rate",
        "Technique",
    ]
    assert [dialog.attributeTable.cellWidget(row, 2).currentText() for row in range(4)] == [
        "Top three",
        "Top three",
        "Top three",
        "Important",
    ]


def testReviewDialogPreservesCustomRoleIDAndAttributeOrderOnSave(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = RoleKnowledgeService(
        tmp_path / "roles",
        TacticVocabulary(),
        {"first_touch", "passing", "technique", "composure"},
    )
    rolePath = tmp_path / "roles" / "role-021.yaml"
    rolePath.parent.mkdir(parents=True, exist_ok=True)
    rolePath.write_text(
        yaml.safe_dump(
            {
                "roleID": 21,
                "displayName": "Deep-Lying Playmaker",
                "inPossession": True,
                "outOfPossession": False,
                "positions": ["DM"],
                "keyAttributes": ["first_touch", "passing", "technique", "composure"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    evidence = RoleProfileEvidence(
        position="DM",
        roleName="Deep-Lying Playmaker",
        phase=TacticalPhase.IN_POSSESSION,
        keyAttributes=("first_touch", "passing", "technique", "composure"),
    )
    dialog = RoleProfileReviewDialog(
        evidence,
        "DM",
        "",
        service,
        existingRoleID=21,
        replaceExisting=True,
        attributeDefinitions=(
            AttributeDefinition("first_touch", "Fir", 1),
            AttributeDefinition("passing", "Pas", 2),
            AttributeDefinition("technique", "Tec", 3),
            AttributeDefinition("composure", "Com", 4),
        ),
    )
    qtbot.addWidget(dialog)

    dialog.attributeTable.setCurrentCell(3, 0)
    moveUp = dialog.findChild(QPushButton, "moveAttributeUpButton")
    assert moveUp is not None
    qtbot.mouseClick(moveUp, Qt.MouseButton.LeftButton)
    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.savedPath is not None
    content = yaml.safe_load(dialog.savedPath.read_text(encoding="utf-8"))
    assert dialog.savedPath.name == "role-021.yaml"
    assert content["roleID"] == 21
    assert content["keyAttributes"] == [
        "first_touch",
        "passing",
        "composure",
        "technique",
    ]


def testReviewDialogPreservesSavedAttributeOrderWhenReopened(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = RoleKnowledgeService(
        tmp_path / "roles",
        TacticVocabulary(),
        {"first_touch", "passing", "technique", "composure"},
    )
    evidence = RoleProfileEvidence(
        position="DM",
        roleName="Deep-Lying Playmaker",
        phase=TacticalPhase.IN_POSSESSION,
        keyAttributes=("first_touch", "passing", "technique", "composure"),
    )
    dialog = RoleProfileReviewDialog(
        evidence,
        "DM",
        "",
        service,
        existingRoleID=21,
        replaceExisting=True,
        attributeDefinitions=(
            AttributeDefinition("first_touch", "Fir", 1),
            AttributeDefinition("passing", "Pas", 2),
            AttributeDefinition("technique", "Tec", 3),
            AttributeDefinition("composure", "Com", 4),
        ),
    )
    qtbot.addWidget(dialog)
    dialog.attributeTable.setCurrentCell(3, 0)
    moveUp = dialog.findChild(QPushButton, "moveAttributeUpButton")
    assert moveUp is not None
    qtbot.mouseClick(moveUp, Qt.MouseButton.LeftButton)
    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()

    saved = yaml.safe_load(dialog.savedPath.read_text(encoding="utf-8"))
    reopened = RoleProfileReviewDialog(
        RoleProfileEvidence(
            position="DM",
            roleName="Deep-Lying Playmaker",
            phase=TacticalPhase.IN_POSSESSION,
            keyAttributes=tuple(saved["keyAttributes"]),
        ),
        "DM",
        "",
        service,
        existingRoleID=21,
        replaceExisting=True,
        attributeImportance=service.importanceLoad(saved["roleID"]),
        attributeDefinitions=(
            AttributeDefinition("first_touch", "Fir", 1),
            AttributeDefinition("passing", "Pas", 2),
            AttributeDefinition("technique", "Tec", 3),
            AttributeDefinition("composure", "Com", 4),
        ),
    )
    qtbot.addWidget(reopened)

    assert [reopened.attributeTable.item(row, 0).text() for row in range(4)] == [
        "First Touch",
        "Passing",
        "Composure",
        "Technique",
    ]


def testReviewDialogNormalizesTypedAttributeNamesBeforeSave(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = RoleKnowledgeService(
        tmp_path,
        TacticVocabulary(),
        {"passing", "aggression"},
    )
    evidence = RoleProfileEvidence(
        position="DM",
        roleName="Defensive Midfielder",
        phase=TacticalPhase.IN_POSSESSION,
        keyAttributes=("passing",),
        displayedPlayerAttributes={"passing": 12},
    )
    dialog = RoleProfileReviewDialog(
        evidence,
        "DM",
        "defensiveMidfielder",
        service,
        attributeDefinitions=(
            AttributeDefinition("passing", "Pas", 1),
            AttributeDefinition("aggression", "Agg", 2),
        ),
    )
    qtbot.addWidget(dialog)

    addButton = dialog.findChild(QPushButton, "addAttributeButton")
    assert addButton is not None
    addButton.click()

    dialog.attributeTable.item(1, 0).setText("Aggression")
    dialog.attributeTable.cellWidget(1, 2).setCurrentText("Important")
    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.savedPath is not None
    content = yaml.safe_load(dialog.savedPath.read_text(encoding="utf-8"))
    assert content["keyAttributes"] == ["passing", "aggression"]
    assert service.importanceLoad(content["roleID"]) == {
        "passing": "topThree",
        "aggression": "important",
    }


def testReviewDialogDeletesExistingProfile(qtbot, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    service = RoleKnowledgeService(
        tmp_path / "roles",
        TacticVocabulary(),
        {"passing"},
    )
    evidence = RoleProfileEvidence(
        position="MC",
        roleName="Advanced Playmaker",
        phase=TacticalPhase.IN_POSSESSION,
        keyAttributes=("passing",),
    )
    draft = service.evidenceVerify(evidence, "MC", "advancedPlaymaker")
    rolePath = service.definitionConfirm(draft)
    requirementsPath = service.weightsConfirm(19, {"passing": 5}, {"passing": "topThree"})
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes
    )
    dialog = RoleProfileReviewDialog(
        evidence,
        "MC",
        "advancedPlaymaker",
        service,
        existingRoleID=19,
    )
    qtbot.addWidget(dialog)

    deleteButton = dialog.findChild(QPushButton, "deleteProfileButton")
    assert deleteButton is not None
    assert deleteButton.isEnabled()

    deleteButton.click()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.profileDeleted is True
    assert rolePath in dialog.deletedPaths
    assert requirementsPath in dialog.deletedPaths
    assert not rolePath.exists()
    assert requirementsPath is not None
    assert not requirementsPath.exists()


def testReviewDialogWarnsOnPositionMismatchAndAllowsProceed(qtbot, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    service = RoleKnowledgeService(
        tmp_path,
        TacticVocabulary(),
        {"passing"},
    )
    evidence = RoleProfileEvidence(
        position="DM",
        roleName="Box-To-Box Midfielder",
        phase=TacticalPhase.IN_POSSESSION,
        abbreviation="BBM",
        keyAttributes=("passing",),
        displayedPlayerAttributes={"passing": 15},
    )
    prompts = []

    def _question(*args, **kwargs):  # type: ignore[no-untyped-def]
        prompts.append(args[2])
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "question", _question)
    dialog = RoleProfileReviewDialog(
        evidence,
        "MC",
        "boxToBoxMidfielder",
        service,
    )
    qtbot.addWidget(dialog)

    assert "DM" in dialog.positionsEdit.text()

    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()

    assert prompts
    assert "Expected position MC" in prompts[0]
    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.savedPath is not None
    content = yaml.safe_load(dialog.savedPath.read_text(encoding="utf-8"))
    assert "DM" in content["positions"]
