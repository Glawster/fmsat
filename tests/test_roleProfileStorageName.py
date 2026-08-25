"""Regression coverage for persisted role-profile screenshot naming."""

from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QDialog

from fmsat.app import window as windowModule
from fmsat.app.window import MainWindow
from fmsat.core.parser import RoleProfileEvidence, TacticVocabulary


def testNewRoleCaptureUsesOcrResolvedRoleIdentity(monkeypatch) -> None:
    """A new-role workflow label must not leak into the persisted screenshot filename."""

    vocabulary = TacticVocabulary()
    persisted: dict[str, str] = {}

    class RoleKnowledgeStub:
        def definitionExists(self, _roleCode: str) -> bool:
            return False

    class ReviewDialogStub:
        savedPath = Path("roles/boxToBoxMidfielder.yaml")

        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def exec(self):  # type: ignore[no-untyped-def]
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        windowModule.QInputDialog,
        "getItem",
        lambda *_args, **_kwargs: ("New role…", True),
    )
    monkeypatch.setattr(windowModule, "RoleProfileReviewDialog", ReviewDialogStub)

    evidence = RoleProfileEvidence(
        position="MC",
        roleName="Box to Box Midfielder",
        abbreviation="BBM",
    )
    importResult = SimpleNamespace(roleProfile=evidence)

    host = SimpleNamespace(
        roleKnowledgeService=RoleKnowledgeStub(),
        tacticVocabulary=vocabulary,
        database=SimpleNamespace(
            tacticRoleCodes=lambda: (),
        ),
        attributes=(),
        screenshotStore=SimpleNamespace(capturesRemove=lambda _paths: None),
        dataChanged=SimpleNamespace(emit=lambda: None),
        statusBar=lambda: SimpleNamespace(showMessage=lambda *_args: None),
        _errorShow=lambda *_args: None,
        _screenshotAcquire=lambda *_args: importResult,
        _screenshotPersist=lambda _result, ownerType, ownerName: (
            persisted.update(ownerType=ownerType, ownerName=ownerName)
            or Path(f"20260810-114016_{ownerType}-{ownerName}_role-profile_21ee2fe2.png")
        ),
    )

    MainWindow.roleProfileImport(host)

    assert persisted == {
        "ownerType": "role",
        "ownerName": "boxToBoxMidfielder",
    }
    assert persisted["ownerName"] != "newRole"
