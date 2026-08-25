from pathlib import Path

import yaml

from fmsat.app.roleAssessmentWeightEditor import RoleAssessmentWeightEditor
from fmsat.core.roleAssessmentPolicy import RoleAssessmentPolicyService


def testWeightEditorLoadsAllPolicyWeightsOnTenPointScale(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    policy = tmp_path / "roleAssessment.yaml"
    policy.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "weightScale": {"minimum": 0, "maximum": 10},
                "roles": {
                    "channelMidfielder": {
                        "attributeWeights": {"passing": 8, "work_rate": 10}
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    service = RoleAssessmentPolicyService(
        policy,
        {"channelMidfielder"},
        {"passing", "work_rate"},
    )

    dialog = RoleAssessmentWeightEditor(service)
    qtbot.addWidget(dialog)

    assert dialog.table.rowCount() == 2
    assert dialog.table.horizontalHeaderItem(2).text() == "Weight (0–10)"
    values = {
        dialog.table.item(row, 1).text(): dialog.table.cellWidget(row, 2).value()
        for row in range(dialog.table.rowCount())
    }
    assert values == {"passing": 8, "work_rate": 10}


def testWeightEditorSavesEditedWeight(qtbot, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    policy = tmp_path / "roleAssessment.yaml"
    policy.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "weightScale": {"minimum": 0, "maximum": 10},
                "roles": {"channelMidfielder": {"attributeWeights": {"passing": 8}}},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    service = RoleAssessmentPolicyService(policy, {"channelMidfielder"}, {"passing"})
    dialog = RoleAssessmentWeightEditor(service)
    qtbot.addWidget(dialog)
    monkeypatch.setattr(
        "fmsat.app.roleAssessmentWeightEditor.QMessageBox.information",
        lambda *args, **kwargs: None,
    )

    dialog.table.cellWidget(0, 2).setValue(9)
    dialog._save()

    saved = yaml.safe_load(policy.read_text(encoding="utf-8"))
    assert saved["roles"]["channelMidfielder"]["attributeWeights"]["passing"] == 9
