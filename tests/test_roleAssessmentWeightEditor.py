from pathlib import Path
from types import SimpleNamespace

import yaml
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from fmsat.app.colourPalette import BUTTON_SELECTED
from fmsat.app.roleAssessmentWeightEditor import RoleAssessmentWeightEditor, _activeDataRole
from fmsat.app.styles import stylePaletteLoad
from fmsat.core.config import AttributeConfigurationService
from fmsat.core.roleAssessmentPolicy import RoleAssessmentPolicyService


class _RoleKnowledgeStub:
    def __init__(self) -> None:
        self.defaultWeights = {
            "channelMidfielder": {"passing": 8, "work_rate": 10},
        }

    def weightsLoad(self, roleCode: str) -> dict[str, int]:
        return dict(self.defaultWeights.get(roleCode, {}))

    def importanceLoad(self, roleCode: str) -> dict[str, str]:
        if roleCode != "channelMidfielder":
            return {}
        return {
            "work_rate": "topThree",
            "passing": "important",
        }


def _paths(tmp_path: Path) -> tuple[Path, Path]:
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
    attributes = tmp_path / "attributes.yaml"
    attributes.write_text(
        yaml.safe_dump(
            {
                "attributes": {
                    "passing": {"abbreviation": "Pas", "order": 1},
                    "work_rate": {
                        "abbreviation": "Wor",
                        "order": 2,
                        "active": False,
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return policy, attributes


def _dialog(tmp_path: Path, *, roleOpen=None):  # type: ignore[no-untyped-def]
    policy, attributesPath = _paths(tmp_path)
    attributeService = AttributeConfigurationService(attributesPath)
    attributes = attributeService.definitionsLoad()
    service = RoleAssessmentPolicyService(
        policy,
        {"channelMidfielder"},
        {"passing", "work_rate"},
    )
    role = SimpleNamespace(
        code="channelMidfielder",
        displayName="Channel Midfielder",
        abbreviations=("CM",),
        positions=("M(C)",),
    )
    dialog = RoleAssessmentWeightEditor(
        service,
        roles={"channelMidfielder": role},
        attributes=attributes,
        roleKnowledge=_RoleKnowledgeStub(),
        attributeService=attributeService,
        roleOpen=roleOpen,
    )
    return dialog, attributesPath


def testWeightEditorShowsRoleByAttributeMatrix(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    dialog, _attributesPath = _dialog(tmp_path)
    qtbot.addWidget(dialog)

    assert dialog.table.rowCount() == 1
    assert dialog.table.columnCount() == 3
    assert dialog.table.horizontalHeaderItem(0).text() == "Role"
    assert dialog.table.horizontalHeaderItem(1).text() == "Pas"
    assert dialog.table.horizontalHeaderItem(2).text() == "Wor"
    assert dialog.table.item(0, 0).text() == "CM"
    assert dialog.table.item(0, 1).text() == "8"
    assert dialog.table.item(0, 2).text() == "10"
    assert dialog.table.item(0, 1).data(Qt.ItemDataRole.UserRole) == "important"
    assert dialog.table.item(0, 2).data(Qt.ItemDataRole.UserRole) == "topThree"
    assert dialog.table.horizontalHeaderItem(2).font().italic() is True
    assert dialog.table.horizontalHeaderItem(2).data(_activeDataRole) is False


def testSemanticTextColoursUseFmsatPalette(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    dialog, _attributesPath = _dialog(tmp_path)
    qtbot.addWidget(dialog)
    palette = stylePaletteLoad()
    delegate = dialog.table.itemDelegate()

    assert delegate.textColour(True, "topThree").name() == QColor(palette["successText"]).name()
    assert delegate.textColour(True, "important").name() == QColor(BUTTON_SELECTED).name()
    assert delegate.textColour(True, "niceToHave").name() == QColor(palette["neutralText"]).name()
    assert delegate.textColour(False, "topThree").name() == QColor(palette["inactiveText"]).name()


def testAttributeHeaderClickTogglesPersistedActiveState(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    changed = []
    dialog, attributesPath = _dialog(tmp_path)
    dialog.attributesChanged = lambda attributes: changed.append(attributes)
    qtbot.addWidget(dialog)

    assert dialog.attributes[1].active is False
    dialog._attributeHeaderClicked(2)

    assert dialog.attributes[1].active is True
    saved = yaml.safe_load(attributesPath.read_text(encoding="utf-8"))
    assert saved["attributes"]["work_rate"]["active"] is True
    assert changed and changed[-1][1].active is True
    assert dialog.table.horizontalHeaderItem(2).font().italic() is False
    assert dialog.table.horizontalHeaderItem(2).data(_activeDataRole) is True


def testClickingRoleIdentifierLaunchesRoleEditor(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    opened = []
    dialog, _attributesPath = _dialog(tmp_path, roleOpen=opened.append)
    qtbot.addWidget(dialog)

    dialog._cellClicked(0, 0)

    assert opened == ["channelMidfielder"]


def testUnweightedCellsAreBlank(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    dialog, _attributesPath = _dialog(tmp_path)
    qtbot.addWidget(dialog)

    dialog.roleKnowledge.defaultWeights["channelMidfielder"] = {"passing": 8}
    dialog._loadCurrent()

    assert dialog.table.item(0, 2).text() == ""


def testRoleRowsUseFrontToBackPositionOrder(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    policy, attributesPath = _paths(tmp_path)
    attributeService = AttributeConfigurationService(attributesPath)
    roles = {
        "goalkeeper": SimpleNamespace(
            code="goalkeeper",
            displayName="Goalkeeper",
            abbreviations=("GK",),
            positions=("GK",),
        ),
        "centreForward": SimpleNamespace(
            code="centreForward",
            displayName="Centre Forward",
            abbreviations=("CFD",),
            positions=("ST(C)",),
        ),
        "channelMidfielder": SimpleNamespace(
            code="channelMidfielder",
            displayName="Channel Midfielder",
            abbreviations=("CM",),
            positions=("M(C)",),
        ),
    }
    service = RoleAssessmentPolicyService(
        policy,
        set(roles),
        {"passing", "work_rate"},
    )
    dialog = RoleAssessmentWeightEditor(
        service,
        roles=roles,
        attributes=attributeService.definitionsLoad(),
        roleKnowledge=_RoleKnowledgeStub(),
        attributeService=attributeService,
    )
    qtbot.addWidget(dialog)

    assert [dialog.table.item(row, 0).text() for row in range(3)] == ["CFD", "CM", "GK"]


def testGoalkeeperOnlyAttributesStayHiddenUntilGoalkeeperRoleSelected(
    qtbot,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    policy = tmp_path / "roleAssessment.yaml"
    policy.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "weightScale": {"minimum": 0, "maximum": 10},
                "roles": {
                    "goalkeeper": {"attributeWeights": {"passing": 4, "handling": 10}},
                    "centreForward": {"attributeWeights": {"passing": 4}},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    attributesPath = tmp_path / "attributes.yaml"
    attributesPath.write_text(
        yaml.safe_dump(
            {
                "attributes": {
                    "passing": {"abbreviation": "Pas", "order": 1},
                    "handling": {"abbreviation": "Han", "order": 2},
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    attributeService = AttributeConfigurationService(attributesPath)
    roles = {
        "centreForward": SimpleNamespace(
            code="centreForward",
            displayName="Centre Forward",
            abbreviations=("CFD",),
            positions=("ST(C)",),
        ),
        "goalkeeper": SimpleNamespace(
            code="goalkeeper",
            displayName="Goalkeeper",
            abbreviations=("GK",),
            positions=("GK",),
        ),
    }
    service = RoleAssessmentPolicyService(policy, set(roles), {"passing", "handling"})
    opened = []
    dialog = RoleAssessmentWeightEditor(
        service,
        roles=roles,
        attributes=attributeService.definitionsLoad(),
        roleKnowledge=SimpleNamespace(),
        attributeService=attributeService,
        roleOpen=opened.append,
    )
    qtbot.addWidget(dialog)

    assert dialog.table.columnCount() == 2
    assert dialog.table.horizontalHeaderItem(1).text() == "Pas"

    goalkeeperRow = next(
        row for row in range(dialog.table.rowCount()) if dialog.table.item(row, 0).text() == "GK"
    )
    dialog._cellClicked(goalkeeperRow, 0)

    assert opened == ["goalkeeper"]
    assert dialog.table.columnCount() == 3
    assert dialog.table.horizontalHeaderItem(2).text() == "Han"