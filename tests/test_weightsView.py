from pathlib import Path
from types import SimpleNamespace

import yaml
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow

from fmsat.app.main import _weightsViewConfigure
from fmsat.core.config import AttributeConfigurationService
from fmsat.core.roleAssessmentPolicy import RoleAssessmentPolicyService


class _Window(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.viewMenu = self.menuBar().addMenu("&View")
        self.tacticsAction = QAction("Tactics", self)
        self.squadsAction = QAction("Squads", self)
        self.rolesAction = QAction("Roles", self)
        self.playersAction = QAction("Players", self)
        self.settingsAction = QAction("Settings", self)
        for action in (
            self.tacticsAction,
            self.squadsAction,
            self.rolesAction,
            self.playersAction,
            self.settingsAction,
        ):
            self.viewMenu.addAction(action)
        self.squadDetailView = SimpleNamespace(attributes=())
        self.attributes = ()

    def roleShow(self, _roleCode: str) -> None:
        return


class _Parser:
    attributes = ()


def testWeightsViewIsPlacedBeforeSettingsByApplicationShell(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    policy = tmp_path / "roleAssessment.yaml"
    policy.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "weightScale": {"minimum": 0, "maximum": 10},
                "roles": {"centreForward": {"attributeWeights": {"finishing": 10}}},
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
                    "finishing": {"abbreviation": "Fin", "order": 1},
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    attributeService = AttributeConfigurationService(attributesPath)
    config = SimpleNamespace(
        attributes=attributeService.definitionsLoad(),
        attributeService=attributeService,
    )
    service = RoleAssessmentPolicyService(policy, {"centreForward"}, {"finishing"})
    vocabulary = SimpleNamespace(
        roles={
            "centreForward": SimpleNamespace(
                displayName="Centre Forward",
                abbreviations=("CFD",),
            )
        }
    )

    window = _Window()
    qtbot.addWidget(window)
    action = _weightsViewConfigure(
        window,  # type: ignore[arg-type]
        service,
        config,  # type: ignore[arg-type]
        vocabulary,  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
        _Parser(),  # type: ignore[arg-type]
        _Parser(),  # type: ignore[arg-type]
    )

    labels = [item.text() for item in window.viewMenu.actions()]
    assert labels == ["Tactics", "Squads", "Roles", "Players", "Weights", "Settings"]
    assert window.weightsAction is action