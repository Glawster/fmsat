"""Tests for user-owned tactic naming independent of OCR evidence."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from fmsat.core.detection import ScreenType
from fmsat.database import Database
from fmsat.database.models import ObjectModelTactic, Tactic
from fmsat.database.tacticNaming import TacticRenameError, tacticRename


def testTacticRenameKeepsScreenshotIdentityAndRenamesLinkedModel(tmp_path) -> None:
    database = Database(tmp_path / "rename.sqlite3")
    database.initialize()
    imported = database.tacticImportSave("formation.png", ScreenType.TACTIC_FORMATION, "Old Name")
    with Session(database.engine) as session, session.begin():
        tactic = session.scalar(select(Tactic).where(Tactic.name == "Old Name"))
        assert tactic is not None
        tacticID = tactic.id
        session.add(
            ObjectModelTactic(
                name="Old Name",
                normalizedName="old name",
                sourceTacticId=tactic.id,
                sourceImportSessionId=imported.id,
            )
        )

    assert tacticRename(database.engine, "Old Name", "New Name") == "New Name"

    with Session(database.engine) as session:
        tactic = session.scalar(select(Tactic).where(Tactic.normalizedName == "new name"))
        model = session.scalar(
            select(ObjectModelTactic).where(ObjectModelTactic.normalizedName == "new name")
        )
        assert tactic is not None and tactic.id == tacticID
        assert model is not None and model.sourceTacticId == tacticID
        assert tactic.screenshots[0].importSessionId == imported.id


def testTacticRenameRejectsExistingName(tmp_path) -> None:
    database = Database(tmp_path / "rename.sqlite3")
    database.initialize()
    database.tacticImportSave("one.png", ScreenType.TACTIC_FORMATION, "One")
    database.tacticImportSave("two.png", ScreenType.TACTIC_FORMATION, "Two")

    with pytest.raises(TacticRenameError, match="already exists"):
        tacticRename(database.engine, "One", "Two")
