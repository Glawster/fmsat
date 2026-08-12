"""Structured-tactic schema and additive migration tests."""

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session, selectinload

from fmsat.core.detection import ScreenType
from fmsat.database import (
    Database,
    ImportSession,
    ObjectModelFormation,
    ObjectModelFormationInstruction,
    ObjectModelPosition,
    ObjectModelPositionInstruction,
    ObjectModelTactic,
    ObjectModelTransitionInstruction,
    StructuredFormationSlot,
    StructuredTacticDefinition,
    StructuredTacticIssue,
    StructuredTeamInstruction,
    Tactic,
)


def testStructuredTacticSchemaPersistsTypedEvidence(tmp_path) -> None:

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
        tactic.structuredDefinition = StructuredTacticDefinition(
            confirmed=False,
            complete=False,
            tacticMetadata={"mentality": "positive"},
            slots=[
                StructuredFormationSlot(
                    slotId="formation-gk-1",
                    phase="formation",
                    position="GK",
                    role="ballPlayingGoalkeeper",
                    duty="support",
                    x=0.5,
                    y=0.91,
                    observedRole="BPGK (Su)",
                    displayedPlayer="Jo Example",
                    confidence=0.94,
                    sourceImportSession=sourceImport,
                    validationState="corrected",
                )
            ],
            instructions=[
                StructuredTeamInstruction(
                    phase="inPossession",
                    category="tempo",
                    canonicalValue="higher",
                    displayValue="Higher",
                    confidence=0.91,
                    sourceImportSession=sourceImport,
                    validationState="extracted",
                )
            ],
            issues=[
                StructuredTacticIssue(
                    code="missingSlots",
                    message="Formation does not yet contain eleven slots",
                    observedText="1 slot",
                )
            ],
        )

    with Session(database.engine) as session:
        stored = session.scalar(
            select(StructuredTacticDefinition).options(
                selectinload(StructuredTacticDefinition.slots),
                selectinload(StructuredTacticDefinition.instructions),
                selectinload(StructuredTacticDefinition.issues),
            )
        )

        assert stored is not None
        assert stored.tacticMetadata == {"mentality": "positive"}
        assert stored.slots[0].sourceImportSessionId == imported.id
        assert stored.slots[0].observedRole == "BPGK (Su)"
        assert stored.instructions[0].canonicalValue == "higher"
        assert stored.instructions[0].displayValue == "Higher"
        assert stored.issues[0].code == "missingSlots"


def testInitializeAddsStructuredSchemaWithoutReplacingLegacyData(tmp_path) -> None:

    databasePath = tmp_path / "legacy.sqlite3"
    legacyDatabase = Database(databasePath)
    legacyDatabase.initialize()
    legacyDatabase.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "Legacy Tactic",
    )

    # Simulate a database created before requirement 006 by removing only the
    # new tables while retaining all existing tactic and import records.
    for model in (
        ObjectModelPositionInstruction,
        ObjectModelFormationInstruction,
        ObjectModelTransitionInstruction,
        ObjectModelPosition,
        ObjectModelFormation,
        ObjectModelTactic,
        StructuredFormationSlot,
        StructuredTeamInstruction,
        StructuredTacticIssue,
        StructuredTacticDefinition,
    ):
        model.__table__.drop(legacyDatabase.engine)

    upgradedDatabase = Database(databasePath)
    upgradedDatabase.initialize()

    tableNames = set(inspect(upgradedDatabase.engine).get_table_names())
    assert {
        "structured_tactic_definitions",
        "structured_formation_slots",
        "structured_team_instructions",
        "structured_tactic_issues",
        "object_model_tactics",
        "object_model_formations",
        "object_model_positions",
        "object_model_formation_instructions",
        "object_model_position_instructions",
        "object_model_transition_instructions",
    }.issubset(tableNames)
    assert upgradedDatabase.tacticsList() == ["Legacy Tactic"]
    assert upgradedDatabase.screenTypesForTactic("Legacy Tactic") == {ScreenType.TACTIC_FORMATION}
