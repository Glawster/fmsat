"""Golden-file acceptance coverage for resolving 007B role-knowledge gaps."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialogButtonBox, QTableWidgetItem

from fmsat.app.roleProfileDialog import RoleProfileReviewDialog
from fmsat.core.config import AttributeDefinition
from fmsat.core.parser import RoleProfileEvidence, TacticalPhase, TacticVocabulary
from fmsat.core.roleKnowledge import RoleKnowledgeService


FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "roleKnowledge"
EXPECTED_ROLE_CODES = {"trackingWinger", "trackingWideMidfielder"}


def _fixtureLoad(path: Path) -> dict[str, object]:
    content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert isinstance(content, dict)
    return content


def _fixturePaths() -> tuple[Path, ...]:
    return tuple(sorted(FIXTURE_DIRECTORY.glob("*.expected.yaml")))


def testRoleKnowledgeGoldenFixturesCoverEveryCurrentUnknownRole() -> None:
    """The final 007B gate must explicitly account for every known semantic Unknown role."""

    fixtures = _fixturePaths()
    assert fixtures
    assert {str(_fixtureLoad(path)["roleCode"]) for path in fixtures} == EXPECTED_ROLE_CODES
    for path in fixtures:
        fixture = _fixtureLoad(path)
        assert fixture["confirmationState"] in {"unresolved", "confirmed"}
        if fixture["confirmationState"] == "unresolved":
            observedAbbreviation = str(fixture.get("observedAbbreviation") or "")
            assert observedAbbreviation
            assert observedAbbreviation.casefold() != "unknown"
            assert fixture.get("expectedDefinition") is None
            assert fixture.get("expectedRequirements") is None


@pytest.mark.parametrize("fixturePath", _fixturePaths(), ids=lambda path: path.stem)
def testUnknownRoleAcceptanceMatchesEvidenceState(qtbot, tmp_path, fixturePath: Path) -> None:  # type: ignore[no-untyped-def]
    """Unresolved roles stay evidence-only; confirmed roles persist their golden YAML."""

    fixture = _fixtureLoad(fixturePath)
    if fixture["confirmationState"] != "confirmed":
        observedAbbreviation = str(fixture.get("observedAbbreviation") or "")
        assert observedAbbreviation
        assert fixture.get("evidence") is None
        assert fixture.get("expectedDefinition") is None
        assert fixture.get("expectedRequirements") is None
        return

    evidenceValues = fixture.get("evidence")
    expectedDefinition = fixture.get("expectedDefinition")
    expectedRequirements = fixture.get("expectedRequirements")
    assert isinstance(evidenceValues, dict)
    assert isinstance(expectedDefinition, dict)
    assert isinstance(expectedRequirements, dict)

    roleCode = str(fixture["roleCode"])
    keyAttributes = tuple(str(value) for value in evidenceValues.get("keyAttributes", ()))
    requirementWeights = expectedRequirements.get("attributeWeights", {})
    assert isinstance(requirementWeights, dict)
    attributeNames = set(keyAttributes) | {str(value) for value in requirementWeights}
    definitions = tuple(
        AttributeDefinition(name, name.replace("_", " ").title(), index)
        for index, name in enumerate(sorted(attributeNames), start=1)
    )

    service = RoleKnowledgeService(
        tmp_path / "roles",
        TacticVocabulary(),
        attributeNames,
    )
    phaseText = str(evidenceValues["phase"])
    phase = TacticalPhase(phaseText)
    evidence = RoleProfileEvidence(
        position=str(evidenceValues["position"]),
        roleName=str(evidenceValues["roleName"]),
        phase=phase,
        abbreviation=(
            str(evidenceValues["abbreviation"])
            if evidenceValues.get("abbreviation") is not None
            else None
        ),
        description=(
            str(evidenceValues["description"])
            if evidenceValues.get("description") is not None
            else None
        ),
        behaviours=tuple(str(value) for value in evidenceValues.get("behaviours", ())),
        keyAttributes=keyAttributes,
        playerInstructions=tuple(
            str(value) for value in evidenceValues.get("playerInstructions", ())
        ),
        sourceImport=str(evidenceValues.get("sourceImport", "role-profile.png")),
        confidence=float(evidenceValues.get("confidence", 1.0)),
    )
    supportedPositions = tuple(str(value) for value in expectedDefinition.get("positions", ()))
    importanceGroups = expectedRequirements.get("importanceGroups", {})
    assert isinstance(importanceGroups, dict)
    importance = {
        str(attribute): str(group)
        for group, attributes in importanceGroups.items()
        if isinstance(attributes, list)
        for attribute in attributes
    }
    weights = {str(attribute): int(value) for attribute, value in requirementWeights.items()}

    dialog = RoleProfileReviewDialog(
        evidence,
        str(evidenceValues["expectedPosition"]),
        roleCode,
        service,
        replaceExisting=True,
        supportedPositions=supportedPositions,
        attributeWeights=weights,
        attributeImportance=importance,
        attributeDefinitions=definitions,
    )
    qtbot.addWidget(dialog)

    if expectedDefinition.get("inPossession") and expectedDefinition.get("outOfPossession"):
        dialog.bothPhasesRadio.setChecked(True)
    elif expectedDefinition.get("outOfPossession"):
        dialog.outOfPossessionRadio.setChecked(True)
    else:
        dialog.inPossessionRadio.setChecked(True)

    for row in range(dialog.attributeTable.rowCount()):
        nameItem = dialog.attributeTable.item(row, 0)
        attribute = str(nameItem.data(Qt.ItemDataRole.UserRole) or "")
        if attribute in weights:
            dialog.attributeTable.setItem(row, 2, QTableWidgetItem(str(weights[attribute])))

    qtbot.mouseClick(
        dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save),
        Qt.MouseButton.LeftButton,
    )

    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.savedPath is not None
    actualDefinition = yaml.safe_load(dialog.savedPath.read_text(encoding="utf-8"))
    assert actualDefinition == expectedDefinition

    requirementCandidates = tuple((tmp_path / "requirements").glob("*.yaml"))
    assert len(requirementCandidates) == 1
    actualRequirements = yaml.safe_load(requirementCandidates[0].read_text(encoding="utf-8"))
    assert actualRequirements == expectedRequirements
