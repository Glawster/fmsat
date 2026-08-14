"""Persist football object-model tactics into dedicated database tables."""

from __future__ import annotations

from dataclasses import dataclass

from fmsat.core.logUtils import getLogger
from fmsat.database.models import (
    ObjectModelFormation,
    ObjectModelFormationInstruction,
    ObjectModelPosition,
    ObjectModelPositionInstruction,
    ObjectModelTactic,
    ObjectModelTransitionInstruction,
    Tactic as DatabaseTactic,
)
from fmsat.football.instruction import InstructionSet
from fmsat.tactics.formation import Formation
from fmsat.tactics.position import Position
from fmsat.tactics.tactic import Tactic
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

logger = getLogger()


@dataclass(frozen=True, slots=True)
class TacticStoreResult:
    """Outcome of persisting one object-model tactic."""

    tacticId: int
    normalizedName: str
    replacedExisting: bool


class TacticStore:
    """Save object-model tactics into dedicated object-model database tables."""

    def __init__(self, engine: Engine) -> None:
        """Create a store bound to one SQLAlchemy engine."""

        self.engine = engine

    ## tactic

    def tacticSave(self, tactic: Tactic) -> TacticStoreResult:
        """Create or replace one stored object-model tactic by normalized name."""

        cleanName = tactic.name.strip()
        if not cleanName:
            raise ValueError("Tactic name is required")
        normalizedName = cleanName.casefold()
        logger.doing(f"saving tactic object model for {cleanName}")

        with Session(self.engine) as session, session.begin():
            sourceTactic = session.scalar(
                select(DatabaseTactic).where(DatabaseTactic.normalizedName == normalizedName)
            )
            stored = session.scalar(
                select(ObjectModelTactic).where(ObjectModelTactic.normalizedName == normalizedName)
            )

            replacedExisting = stored is not None
            logger.value("replacing existing tactic object model", replacedExisting)
            if stored is None:
                stored = ObjectModelTactic(
                    name=cleanName,
                    normalizedName=normalizedName,
                )
                session.add(stored)
            else:
                # Replacing child rows through relationship clear keeps the
                # operation deterministic and leaves one canonical row per name.
                stored.formations.clear()
                stored.transitionInstructions.clear()
                stored.name = cleanName
                # Flush orphan deletions first so unique constraints on
                # replacement child rows do not conflict in the same unit of work.
                session.flush()

            stored.sourceTactic = sourceTactic
            stored.sourceImportSessionId = (
                max(
                    (capture.importSessionId for capture in sourceTactic.screenshots),
                    default=None,
                )
                if sourceTactic is not None
                else None
            )
            self._formationStore(stored, "inPossession", tactic.inPossession)
            self._formationStore(stored, "outOfPossession", tactic.outOfPossession)
            self._transitionStore(stored, tactic)
            session.flush()

            logger.info(
                f"stored tactic model: {len(tactic.inPossession.positions)} "
                "in-possession positions, "
                f"{len(tactic.outOfPossession.positions)} out-of-possession positions, "
                f"{len(tactic.inPossession.instructions)} in-possession instructions, "
                f"{len(tactic.outOfPossession.instructions)} out-of-possession instructions"
            )

            return TacticStoreResult(
                tacticId=stored.id,
                normalizedName=normalizedName,
                replacedExisting=replacedExisting,
            )

    ## formation

    def _formationStore(
        self,
        storedTactic: ObjectModelTactic,
        phase: str,
        formation: Formation,
    ) -> None:
        """Persist one formation, including positions and team instructions."""

        storedFormation = ObjectModelFormation(
            phase=phase,
            name=formation.name,
        )
        storedFormation.teamInstructions.extend(
            ObjectModelFormationInstruction(
                category=instruction.name,
                valueName=value.name,
                valueDescription=value.description,
            )
            for instruction, value in self._instructionItems(formation.instructions)
        )

        for index, position in enumerate(formation.positions):
            storedFormation.positions.append(self._positionStore(position, index))

        storedTactic.formations.append(storedFormation)

    def _positionStore(self, position: Position, index: int) -> ObjectModelPosition:
        """Persist one formation position and any explicit player instructions."""

        storedPosition = ObjectModelPosition(
            ordinal=index,
            positionIdentity=position.identity.value,
            roleIdentity=position.role.identity.value,
            roleProfileName=position.roleProfile.name,
            roleProfileDescription=position.roleProfile.description,
            slotId=position.slotId,
            duty=position.duty,
            x=position.x,
            y=position.y,
            displayedPlayer=position.player,
            confidence=position.confidence,
            sourceImportSessionId=position.sourceImportSessionId,
            validationState=position.validationState,
        )
        storedPosition.instructions.extend(
            ObjectModelPositionInstruction(
                category=instruction.name,
                valueName=value.name,
                valueDescription=value.description,
            )
            for instruction, value in self._instructionItems(position.instructions)
        )
        return storedPosition

    ## transition

    def _transitionStore(self, storedTactic: ObjectModelTactic, tactic: Tactic) -> None:
        """Persist transition instruction selections for one tactic."""

        storedTactic.transitionInstructions.extend(
            ObjectModelTransitionInstruction(
                category=instruction.name,
                valueName=value.name,
                valueDescription=value.description,
            )
            for instruction, value in self._instructionItems(tactic.transition.instructions)
        )

    ## instructions

    def _instructionItems(self, instructionSet: InstructionSet):
        """Return instruction/value pairs with deterministic instruction ordering."""

        return sorted(instructionSet.items(), key=lambda item: item[0].name.casefold())
