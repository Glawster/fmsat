"""Tests for loading tactic models from object-model and structured sources."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from fmsat.core.builder.tacticBuilder import TacticBuilder
from fmsat.core.builder.tacticModelLoader import TacticModelLoader
from fmsat.core.builder.tacticStore import TacticStore
from fmsat.core.detection import ScreenType
from fmsat.database import (
    Database,
    ImportSession,
    StructuredFormationSlot,
    ScreenshotDerivedTacticDefinition,
    StructuredTacticIssue,
    Tactic,
)
from fmsat.football.role import Role
from fmsat.football.roleIdentity import RoleIdentity
from fmsat.football.roleProfile import RoleProfile
from fmsat.tactics.formation import Formation
from fmsat.tactics.position import Position
from fmsat.tactics.positionIdentity import PositionIdentity
from fmsat.tactics.tactic import Tactic as ModelTactic


def _objectModelSample(name: str, inPossessionName: str) -> ModelTactic:
    """Return one small object-model tactic for loader tests."""

    goalkeeper = Role(identity=RoleIdentity.GK)
    centreBack = Role(identity=RoleIdentity.CB)
    centreForward = Role(identity=RoleIdentity.CF)
    defendProfile = RoleProfile(name="Defend", description="Defend duty")
    attackProfile = RoleProfile(name="Attack", description="Attack duty")
    inPossession = Formation(
        name=inPossessionName,
        positions=[
            Position(
                PositionIdentity.GK,
                goalkeeper,
                defendProfile,
                slotId="in-gk",
                duty="defend",
                x=0.5,
                y=0.9,
                player="Example Keeper",
                confidence=0.96,
                sourceImportSessionId=1,
                validationState="confirmed",
            ),
            Position(PositionIdentity.DC, centreBack, defendProfile),
            Position(PositionIdentity.ST, centreForward, attackProfile),
        ],
    )
    outOfPossession = Formation(
        name="Out Shape",
        positions=[
            Position(PositionIdentity.GK, goalkeeper, defendProfile),
            Position(PositionIdentity.DC, centreBack, defendProfile),
            Position(PositionIdentity.ST, centreForward, attackProfile),
        ],
    )
    return ModelTactic(name=name, inPossession=inPossession, outOfPossession=outOfPossession)


def testLoaderPrefersSavedObjectModelOverStructuredDefinition(tmp_path) -> None:
    """When both sources exist, the saved object-model tactic should be loaded."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    imported = database.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "High Press",
    )
    with Session(database.engine) as session, session.begin():
        tactic = session.scalar(select(Tactic).where(Tactic.normalizedName == "high press"))
        sourceImport = session.get(ImportSession, imported.id)
        assert tactic is not None
        assert sourceImport is not None
        tactic.structuredDefinition = ScreenshotDerivedTacticDefinition(
            confirmed=True,
            complete=True,
            tacticMetadata={"inPossessionName": "Structured Shape"},
            slots=[
                StructuredFormationSlot(
                    slotId="slot-1",
                    phase="formation",
                    position="GK",
                    role="goalkeeper",
                    duty="defend",
                    x=0.50,
                    y=0.90,
                    observedRole="",
                    confidence=0.95,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                ),
                StructuredFormationSlot(
                    slotId="slot-2",
                    phase="formation",
                    position="DC",
                    role="centreBack",
                    duty="defend",
                    x=0.50,
                    y=0.70,
                    observedRole="",
                    confidence=0.95,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                ),
                StructuredFormationSlot(
                    slotId="slot-3",
                    phase="formation",
                    position="ST",
                    role="centreForward",
                    duty="attack",
                    x=0.50,
                    y=0.10,
                    observedRole="",
                    confidence=0.95,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                ),
            ],
            instructions=[],
        )

    store = TacticStore(database.engine)
    store.tacticSave(_objectModelSample("High Press", "Saved Shape"))

    loader = TacticModelLoader(database.engine)
    loaded = loader.tacticLoad("High Press")

    assert loaded.tactic is not None
    assert loaded.source == "objectModel"
    assert loaded.phaseSlots == {}
    assert loaded.tactic.inPossession.name == "Saved Shape"
    loadedKeeper = loaded.tactic.inPossession.positions[0]
    assert loadedKeeper.slotId == "in-gk"
    assert loadedKeeper.duty == "defend"
    assert loadedKeeper.x == 0.5
    assert loadedKeeper.y == 0.9
    assert loadedKeeper.player == "Example Keeper"
    assert loadedKeeper.confidence == 0.96
    assert loadedKeeper.sourceImportSessionId == 1
    assert loadedKeeper.validationState == "confirmed"


def testSavedObjectModelPreservesStructuredExtractionIssues(tmp_path) -> None:
    """Saved models must still expose warnings from their source extraction."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    imported = database.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "Metadata Gap",
    )
    with Session(database.engine) as session, session.begin():
        tactic = session.scalar(
            select(Tactic).where(Tactic.normalizedName == "metadata gap")
        )
        assert tactic is not None
        tactic.structuredDefinition = ScreenshotDerivedTacticDefinition(
            confirmed=False,
            complete=True,
            tacticMetadata={},
            slots=[],
            instructions=[],
            issues=[
                StructuredTacticIssue(
                    code="metadataExtractionIncomplete",
                    message="Formation screenshot did not expose formation name and mentality",
                )
            ],
        )

    TacticStore(database.engine).tacticSave(_objectModelSample("Metadata Gap", "Saved Shape"))

    loaded = TacticModelLoader(database.engine).tacticLoad("Metadata Gap")

    assert loaded.source == "objectModel"
    assert [issue.code for issue in loaded.issues] == ["metadataExtractionIncomplete"]
    assert "formation name and mentality" in loaded.issues[0].message


def testLoaderDoesNotInferPhaseSlotsFromFormationEvidence(tmp_path) -> None:
    """Formation evidence must not be copied into unobserved phase formations."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    imported = database.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "Fallback Press",
    )
    with Session(database.engine) as session, session.begin():
        tactic = session.scalar(select(Tactic).where(Tactic.normalizedName == "fallback press"))
        sourceImport = session.get(ImportSession, imported.id)
        assert tactic is not None
        assert sourceImport is not None
        tactic.structuredDefinition = ScreenshotDerivedTacticDefinition(
            confirmed=False,
            complete=False,
            tacticMetadata={"inPossessionName": "Structured Fallback"},
            slots=[
                StructuredFormationSlot(
                    slotId="slot-1",
                    phase="formation",
                    position="GK",
                    role="goalkeeper",
                    duty="defend",
                    x=0.50,
                    y=0.90,
                    observedRole="",
                    confidence=0.95,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                ),
                StructuredFormationSlot(
                    slotId="slot-2",
                    phase="formation",
                    position="DC",
                    role="centreBack",
                    duty="defend",
                    x=0.50,
                    y=0.70,
                    observedRole="",
                    confidence=0.95,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                ),
                StructuredFormationSlot(
                    slotId="slot-3",
                    phase="formation",
                    position="ST",
                    role="centreForward",
                    duty="attack",
                    x=0.50,
                    y=0.10,
                    observedRole="",
                    confidence=0.95,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                ),
            ],
            instructions=[],
        )

    loader = TacticModelLoader(database.engine)
    built = loader.tacticLoad("Fallback Press")
    direct = TacticBuilder(database.engine).tacticBuild("Fallback Press")

    assert built.tactic is None
    assert built.source == "structured"
    assert direct.tactic is None
    assert sum(issue.code == "emptyFormation" for issue in built.issues) == 2
