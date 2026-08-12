"""Load football object-model tactics from persisted tactic data sources."""

from __future__ import annotations

from dataclasses import dataclass, field

from fmsat.core.builder.tacticBuilder import TacticBuildIssue, TacticBuilder
from fmsat.database.models import (
    ObjectModelFormation,
    ObjectModelFormationInstruction,
    ObjectModelPosition,
    ObjectModelPositionInstruction,
    ObjectModelTactic,
    ObjectModelTransitionInstruction,
    StructuredTacticDefinition,
    Tactic as DatabaseTactic,
)
from fmsat.football.instruction import Instruction, InstructionSet, InstructionValue
from fmsat.football.role import Role
from fmsat.football.roleIdentity import RoleIdentity
from fmsat.football.roleProfile import RoleProfile
from fmsat.tactics.formation import Formation
from fmsat.tactics.position import Position
from fmsat.tactics.positionIdentity import PositionIdentity
from fmsat.tactics.tactic import Tactic
from fmsat.tactics.transition import Transition
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, selectinload


@dataclass(frozen=True, slots=True)
class TacticModelLoadResult:
    """Outcome of loading one tactic object for UI presentation."""

    tactic: Tactic | None
    source: str
    issues: tuple[TacticBuildIssue, ...]
    complete: bool
    confirmed: bool
    metadata: dict[str, str] = field(default_factory=dict)
    phaseSlots: dict[str, tuple[tuple[str, str, str, str, float, float, str | None], ...]] = field(
        default_factory=dict
    )


class TacticModelLoader:
    """Load one tactic by preferring saved object-model rows over OCR structure."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.structuredBuilder = TacticBuilder(engine)

    ## tactic

    def tacticLoad(
        self,
        tacticName: str,
        *,
        preferStructured: bool = False,
    ) -> TacticModelLoadResult:
        """Load one tactic, preferring object-model persistence when available."""

        cleanName = tacticName.strip()
        if not cleanName:
            return TacticModelLoadResult(
                tactic=None,
                source="none",
                issues=(TacticBuildIssue("invalidTacticName", "Tactic name is empty"),),
                complete=False,
                confirmed=False,
                metadata={},
                phaseSlots={},
            )

        with Session(self.engine) as session:
            sourceTactic = session.scalar(
                select(DatabaseTactic)
                .where(DatabaseTactic.normalizedName == cleanName.casefold())
                .options(
                    selectinload(DatabaseTactic.structuredDefinition).selectinload(
                        StructuredTacticDefinition.slots
                    ),
                    selectinload(DatabaseTactic.structuredDefinition).selectinload(
                        StructuredTacticDefinition.issues
                    ),
                )
            )
            structuredMetadata, structuredSlots = self._structuredSnapshot(sourceTactic)
            objectModel = session.scalar(
                select(ObjectModelTactic)
                .where(ObjectModelTactic.normalizedName == cleanName.casefold())
                .options(
                    selectinload(ObjectModelTactic.sourceTactic)
                    .selectinload(DatabaseTactic.structuredDefinition)
                    .selectinload(StructuredTacticDefinition.slots),
                    selectinload(ObjectModelTactic.sourceTactic)
                    .selectinload(DatabaseTactic.structuredDefinition)
                    .selectinload(StructuredTacticDefinition.issues),
                    selectinload(ObjectModelTactic.formations).selectinload(
                        ObjectModelFormation.positions
                    ),
                    selectinload(ObjectModelTactic.formations).selectinload(
                        ObjectModelFormation.teamInstructions
                    ),
                    selectinload(ObjectModelTactic.formations)
                    .selectinload(ObjectModelFormation.positions)
                    .selectinload(ObjectModelPosition.instructions),
                    selectinload(ObjectModelTactic.transitionInstructions),
                )
            )

        if objectModel is not None and not preferStructured:
            # If the object model was derived from structured rows, preserve
            # that richer metadata for the tactic detail workspace.
            if objectModel.sourceTactic is not None:
                structuredMetadata, structuredSlots = self._structuredSnapshot(
                    objectModel.sourceTactic
                )
            return TacticModelLoadResult(
                tactic=self._tacticFromObjectModel(objectModel),
                source="objectModel",
                issues=self._structuredIssues(objectModel.sourceTactic),
                complete=True,
                confirmed=True,
                metadata=structuredMetadata,
                phaseSlots=structuredSlots,
            )

        built = self.structuredBuilder.tacticBuild(cleanName)
        return TacticModelLoadResult(
            tactic=built.tactic,
            source="structured",
            issues=built.issues,
            complete=built.complete,
            confirmed=built.confirmed,
            metadata=structuredMetadata,
            phaseSlots=structuredSlots,
        )

    @staticmethod
    def _structuredIssues(tactic: DatabaseTactic | None) -> tuple[TacticBuildIssue, ...]:
        """Return persisted extraction/review findings for one source tactic."""

        if tactic is None or tactic.structuredDefinition is None:
            return ()
        return tuple(
            TacticBuildIssue(issue.code, issue.message)
            for issue in tactic.structuredDefinition.issues
        )

    ## mapping

    def _formationFromObjectModel(self, model: ObjectModelFormation) -> Formation:
        """Map one persisted object-model phase into one Formation object."""

        positions = [
            self._positionFromObjectModel(position)
            for position in sorted(model.positions, key=lambda item: item.ordinal)
        ]
        return Formation(
            name=model.name,
            positions=positions,
            instructions=self._instructionSetBuild(model.teamInstructions),
        )

    @staticmethod
    def _instructionSetBuild(rows) -> InstructionSet:
        """Build instruction/value pairs from persisted instruction rows."""

        instructionSet: InstructionSet = {}
        for row in sorted(rows, key=lambda item: item.category.casefold()):
            instruction = Instruction(name=row.category)
            value = InstructionValue(
                name=row.valueName,
                description=row.valueDescription or row.valueName,
            )
            instructionSet[instruction] = value
        return instructionSet

    def _positionFromObjectModel(self, model: ObjectModelPosition) -> Position:
        """Map one persisted object-model position into one Position object."""

        identity = PositionIdentity(model.positionIdentity)
        role = Role(identity=RoleIdentity(model.roleIdentity))
        profile = RoleProfile(
            name=model.roleProfileName,
            description=model.roleProfileDescription,
        )
        return Position(
            identity=identity,
            role=role,
            roleProfile=profile,
            instructions=self._instructionSetBuild(model.instructions),
        )

    def _tacticFromObjectModel(self, model: ObjectModelTactic) -> Tactic:
        """Map one persisted object-model tactic row back into a Tactic object."""

        formations = {formation.phase: formation for formation in model.formations}
        inPossession = formations.get("inPossession")
        outOfPossession = formations.get("outOfPossession")
        if inPossession is None or outOfPossession is None:
            return Tactic(
                name=model.name,
                inPossession=Formation(name="inPossession", positions=[]),
                outOfPossession=Formation(name="outOfPossession", positions=[]),
                transition=Transition(),
            )
        return Tactic(
            name=model.name,
            inPossession=self._formationFromObjectModel(inPossession),
            outOfPossession=self._formationFromObjectModel(outOfPossession),
            transition=Transition(
                instructions=self._instructionSetBuild(model.transitionInstructions)
            ),
        )

    @staticmethod
    def _structuredSnapshot(
        tactic: DatabaseTactic | None,
    ) -> tuple[
        dict[str, str],
        dict[str, tuple[tuple[str, str, str, str, float, float, str | None], ...]],
    ]:
        """Return structured metadata and slots when persisted for this tactic."""

        if tactic is None or tactic.structuredDefinition is None:
            return {}, {}

        definition = tactic.structuredDefinition
        metadata = {
            str(key): str(value)
            for key, value in definition.tacticMetadata.items()
            if isinstance(key, str) and isinstance(value, str)
        }
        phaseSlots: dict[str, list[tuple[str, str, str, str, float, float, str | None]]] = {}
        for slot in sorted(
            definition.slots,
            key=lambda item: (item.phase.casefold(), item.slotId.casefold()),
        ):
            if slot.position is None or slot.role is None or slot.duty is None:
                continue
            phaseSlots.setdefault(slot.phase, []).append(
                (
                    slot.slotId,
                    slot.position,
                    slot.role,
                    slot.duty,
                    slot.x,
                    slot.y,
                    slot.displayedPlayer,
                )
            )

        return metadata, {phase: tuple(values) for phase, values in phaseSlots.items()}
