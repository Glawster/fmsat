"""Persistence tests for storing football object-model tactics."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from fmsat.core.builder.tacticStore import TacticStore
from fmsat.core.detection import ScreenType
from fmsat.database import (
    Database,
    ObjectModelFormation,
    ObjectModelTactic,
    Tactic as DatabaseTactic,
)
from fmsat.football.instruction import Instruction, InstructionValue
from fmsat.football.role import Role
from fmsat.football.roleIdentity import RoleIdentity
from fmsat.football.roleProfile import RoleProfile
from fmsat.tactics.formation import Formation
from fmsat.tactics.position import Position
from fmsat.tactics.positionIdentity import PositionIdentity
from fmsat.tactics.tactic import Tactic
from fmsat.tactics.transition import Transition


def _sampleTactic(
    name: str = "High Press",
    sourceImportSessionId: int | None = None,
) -> Tactic:
    """Return a small but complete tactic model for persistence tests."""

    attackingWidth = Instruction(name="Attacking Width")
    possessionLost = Instruction(name="Possession Lost")

    stayWider = InstructionValue(name="Stay Wider", description="Stay Wider")
    counterPress = InstructionValue(name="Counter Press", description="Counter-Press")

    goalkeeper = Role(identity=RoleIdentity.GK)
    centreBack = Role(identity=RoleIdentity.CB)
    wingBack = Role(identity=RoleIdentity.WB)
    centreForward = Role(identity=RoleIdentity.CF)

    defendProfile = RoleProfile(name="Defend", description="Defend duty")
    supportProfile = RoleProfile(name="Support", description="Support duty")
    attackProfile = RoleProfile(name="Attack", description="Attack duty")

    inPossession = Formation(
        name="3-4-2-1",
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
                sourceImportSessionId=sourceImportSessionId,
                validationState="confirmed",
            ),
            Position(PositionIdentity.DC, centreBack, defendProfile),
            Position(PositionIdentity.WBL, wingBack, supportProfile),
            Position(PositionIdentity.ST, centreForward, attackProfile),
        ],
        instructions={attackingWidth: stayWider},
    )

    outOfPossession = Formation(
        name="4-4-1-1",
        positions=[
            Position(PositionIdentity.GK, goalkeeper, defendProfile),
            Position(PositionIdentity.DL, wingBack, supportProfile),
            Position(PositionIdentity.DC, centreBack, defendProfile),
            Position(PositionIdentity.ST, centreForward, attackProfile),
        ],
        instructions={attackingWidth: stayWider},
    )

    transition = Transition(instructions={possessionLost: counterPress})

    return Tactic(
        name=name,
        inPossession=inPossession,
        outOfPossession=outOfPossession,
        transition=transition,
    )


def testStorePersistsTacticIntoObjectModelSchema(tmp_path) -> None:
    """Saving one tactic should populate only the new object-model schema."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    database.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "High Press",
    )

    store = TacticStore(database.engine)
    result = store.tacticSave(_sampleTactic(sourceImportSessionId=1))

    assert result.replacedExisting is False

    with Session(database.engine) as session:
        stored = session.scalar(
            select(ObjectModelTactic)
            .where(ObjectModelTactic.normalizedName == "high press")
            .options(
                selectinload(ObjectModelTactic.formations).selectinload(
                    ObjectModelFormation.positions
                ),
                selectinload(ObjectModelTactic.formations).selectinload(
                    ObjectModelFormation.teamInstructions
                ),
                selectinload(ObjectModelTactic.transitionInstructions),
                selectinload(ObjectModelTactic.sourceTactic),
            )
        )
        assert stored is not None
        assert stored.name == "High Press"
        assert stored.sourceTactic is not None
        assert stored.sourceTactic.normalizedName == "high press"
        assert stored.sourceImportSessionId == 1
        assert len(stored.formations) == 2

        inPossession = next(
            formation for formation in stored.formations if formation.phase == "inPossession"
        )
        outOfPossession = next(
            formation for formation in stored.formations if formation.phase == "outOfPossession"
        )

        assert inPossession.name == "3-4-2-1"
        assert outOfPossession.name == "4-4-1-1"
        assert [position.positionIdentity for position in inPossession.positions] == [
            "GK",
            "DC",
            "WBL",
            "ST",
        ]
        assert inPossession.teamInstructions[0].category == "Attacking Width"
        goalkeeperPosition = inPossession.positions[0]
        assert goalkeeperPosition.slotId == "in-gk"
        assert goalkeeperPosition.duty == "defend"
        assert goalkeeperPosition.x == 0.5
        assert goalkeeperPosition.y == 0.9
        assert goalkeeperPosition.displayedPlayer is None
        assert goalkeeperPosition.confidence == 0.96
        assert goalkeeperPosition.sourceImportSessionId == 1
        assert goalkeeperPosition.validationState == "confirmed"
        assert stored.transitionInstructions[0].category == "Possession Lost"

        # Confirm legacy structured extraction rows remain separate and untouched.
        source = session.scalar(
            select(DatabaseTactic).where(DatabaseTactic.normalizedName == "high press")
        )
        assert source is not None
        assert source.structuredDefinition is None


def testStoreReplacesExistingObjectModelRowsByName(tmp_path) -> None:
    """Saving the same tactic name again should replace child rows deterministically."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()

    store = TacticStore(database.engine)
    first = _sampleTactic("Counter Press")
    second = _sampleTactic("Counter Press")
    second.inPossession.name = "3-2-4-1"
    second.inPossession.instructions = {
        Instruction(name="Attacking Width"): InstructionValue(
            name="Narrow",
            description="Narrow",
        )
    }

    firstResult = store.tacticSave(first)
    secondResult = store.tacticSave(second)

    assert firstResult.replacedExisting is False
    assert secondResult.replacedExisting is True
    assert firstResult.tacticId == secondResult.tacticId

    with Session(database.engine) as session:
        stored = session.scalar(
            select(ObjectModelTactic)
            .where(ObjectModelTactic.normalizedName == "counter press")
            .options(selectinload(ObjectModelTactic.formations))
        )
        assert stored is not None
        assert len(stored.formations) == 2
        inPossession = next(
            formation for formation in stored.formations if formation.phase == "inPossession"
        )
        assert inPossession.name == "3-2-4-1"
        assert len(inPossession.teamInstructions) == 1
        assert inPossession.teamInstructions[0].valueName == "Narrow"
