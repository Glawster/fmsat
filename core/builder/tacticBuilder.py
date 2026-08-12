"""Build football object-model tactics from persisted structured DB data."""

from __future__ import annotations

from dataclasses import dataclass

from fmsat.database.models import (
    StructuredFormationSlot,
    StructuredTacticDefinition,
    StructuredTeamInstruction,
    Tactic as DatabaseTactic,
)
from fmsat.football.instruction import Instruction, InstructionSet, InstructionValue
from fmsat.football.role import Role
from fmsat.football.roleIdentity import RoleIdentity
from fmsat.football.roleProfile import RoleProfile
from fmsat.football.roleVocabulary import RoleVocabulary
from fmsat.tactics.formation import Formation
from fmsat.tactics.position import Position
from fmsat.tactics.positionIdentity import PositionIdentity
from fmsat.tactics.tactic import Tactic
from fmsat.tactics.transition import Transition
from sqlalchemy import Engine, Select, select
from sqlalchemy.orm import Session, selectinload


@dataclass(frozen=True, slots=True)
class TacticBuildIssue:
    """One warning or gap discovered while translating DB data."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class TacticBuildResult:
    """Result of building one tactic object from the structured DB definition."""

    tactic: Tactic | None
    issues: tuple[TacticBuildIssue, ...]
    complete: bool
    confirmed: bool


class TacticBuilder:
    """Load a persisted tactic and translate it into the football object model.

    The builder intentionally reports partial coverage instead of raising when
    extraction data is incomplete. This lets callers render a tactic preview and
    decide whether further screenshot extraction/review is needed.
    """

    _POSITION_ORDER = {identity: index for index, identity in enumerate(PositionIdentity)}

    def __init__(self, engine: Engine) -> None:
        """Create a builder bound to a SQLAlchemy engine."""

        self.engine = engine

    ## tactic

    def tacticBuild(self, tacticName: str) -> TacticBuildResult:
        """Build one football-model tactic from the database by tactic name."""

        issues: list[TacticBuildIssue] = []
        cleanName = tacticName.strip()
        if not cleanName:
            issues.append(TacticBuildIssue("invalidTacticName", "Tactic name is empty"))
            return TacticBuildResult(None, tuple(issues), False, False)

        with Session(self.engine) as session:
            definition = self._definitionLoad(session, cleanName)

        if definition is None:
            issues.append(
                TacticBuildIssue(
                    "missingStructuredDefinition",
                    f"No structured tactic definition exists for {cleanName!r}",
                )
            )
            return TacticBuildResult(None, tuple(issues), False, False)

        # Extraction and review findings are persisted with the structured
        # definition.  They remain relevant when the rows can still be mapped
        # into a complete football object model, so expose them to callers
        # alongside mapping issues discovered by this builder.
        issues.extend(TacticBuildIssue(issue.code, issue.message) for issue in definition.issues)

        formationSlots = self._slotsForPhase(definition, "formation")
        inPossessionSlots = self._slotsForPhase(definition, "inPossession")
        outOfPossessionSlots = self._slotsForPhase(definition, "outOfPossession")
        instructionCatalog = self._instructionCatalogBuild(definition)

        # Formation slots are the canonical fallback when phase-specific slots
        # are not yet extracted or reviewed.
        if not inPossessionSlots and formationSlots:
            inPossessionSlots = formationSlots
            issues.append(
                TacticBuildIssue(
                    "inPossessionFallbackToFormation",
                    "In-possession slots are missing; using formation slots as fallback",
                )
            )
        if not outOfPossessionSlots and formationSlots:
            outOfPossessionSlots = formationSlots
            issues.append(
                TacticBuildIssue(
                    "outOfPossessionFallbackToFormation",
                    "Out-of-possession slots are missing; using formation slots as fallback",
                )
            )

        inPossessionModel = self._formationBuild(
            formationName=definition.tacticMetadata.get("inPossessionName", "inPossession"),
            slots=inPossessionSlots,
            definition=definition,
            instructionCatalog=instructionCatalog,
            phaseName="inPossession",
            issues=issues,
        )
        outOfPossessionModel = self._formationBuild(
            formationName=definition.tacticMetadata.get("outOfPossessionName", "outOfPossession"),
            slots=outOfPossessionSlots,
            definition=definition,
            instructionCatalog=instructionCatalog,
            phaseName="outOfPossession",
            issues=issues,
        )
        transitionModel = self._transitionBuild(definition, instructionCatalog, issues)

        # A tactic cannot be built if either required phase has no valid slots.
        if inPossessionModel is None or outOfPossessionModel is None:
            return TacticBuildResult(
                None,
                tuple(issues),
                definition.complete,
                definition.confirmed,
            )

        tacticModel = Tactic(
            name=cleanName,
            inPossession=inPossessionModel,
            outOfPossession=outOfPossessionModel,
            transition=transitionModel,
        )
        return TacticBuildResult(
            tactic=tacticModel,
            issues=tuple(issues),
            complete=definition.complete,
            confirmed=definition.confirmed,
        )

    ## definition

    def _definitionLoad(
        self,
        session: Session,
        tacticName: str,
    ) -> StructuredTacticDefinition | None:
        """Return the eager-loaded structured definition for one tactic."""

        query: Select[tuple[DatabaseTactic]] = (
            select(DatabaseTactic)
            .where(DatabaseTactic.normalizedName == tacticName.casefold())
            .options(
                selectinload(DatabaseTactic.structuredDefinition).selectinload(
                    StructuredTacticDefinition.slots
                ),
                selectinload(DatabaseTactic.structuredDefinition).selectinload(
                    StructuredTacticDefinition.instructions
                ),
                selectinload(DatabaseTactic.structuredDefinition).selectinload(
                    StructuredTacticDefinition.issues
                ),
            )
        )
        record = session.scalar(query)
        if record is None:
            return None
        return record.structuredDefinition

    ## formation

    def _formationBuild(
        self,
        formationName: str,
        slots: list[StructuredFormationSlot],
        definition: StructuredTacticDefinition,
        instructionCatalog: dict[str, Instruction],
        phaseName: str,
        issues: list[TacticBuildIssue],
    ) -> Formation | None:
        """Build one phase formation from structured slots and instructions."""

        positions: list[Position] = []
        roleCache: dict[RoleIdentity, Role] = {}
        profileCache: dict[tuple[RoleIdentity, str], RoleProfile] = {}

        for slot in sorted(slots, key=self._slotSortKey):
            position = self._positionBuild(
                slot=slot,
                phaseName=phaseName,
                issues=issues,
                roleCache=roleCache,
                profileCache=profileCache,
            )
            if position is not None:
                positions.append(position)

        if not positions:
            issues.append(
                TacticBuildIssue(
                    "emptyFormation",
                    f"No valid {phaseName} positions could be mapped into the object model",
                )
            )
            return None

        if len(positions) < 11:
            issues.append(
                TacticBuildIssue(
                    "incompleteFormation",
                    f"{phaseName} has {len(positions)} mapped positions; 11 expected",
                )
            )

        return Formation(
            name=formationName,
            positions=positions,
            instructions=self._instructionsBuild(definition, instructionCatalog, phaseName),
        )

    def _positionBuild(
        self,
        slot: StructuredFormationSlot,
        phaseName: str,
        issues: list[TacticBuildIssue],
        roleCache: dict[RoleIdentity, Role],
        profileCache: dict[tuple[RoleIdentity, str], RoleProfile],
    ) -> Position | None:
        """Build one position from one slot, or report why it cannot be mapped."""

        identity = self._positionIdentityParse(slot.position)
        if identity is None:
            issues.append(
                TacticBuildIssue(
                    "unknownPositionIdentity",
                    f"{phaseName} slot {slot.slotId!r} has unknown position {slot.position!r}",
                )
            )
            return None

        roleIdentity = self._roleIdentityParse(slot.role, slot.observedRole)
        if roleIdentity is None:
            issues.append(
                TacticBuildIssue(
                    "unknownRoleIdentity",
                    f"{phaseName} slot {slot.slotId!r} has unknown role {slot.role!r}",
                )
            )
            return None

        role = roleCache.get(roleIdentity)
        if role is None:
            role = Role(identity=roleIdentity)
            roleCache[roleIdentity] = role

        profileKey = (roleIdentity, slot.duty or "default")
        roleProfile = profileCache.get(profileKey)
        if roleProfile is None:
            profileName = slot.duty.capitalize() if slot.duty else "Default"
            roleProfile = RoleProfile(
                name=profileName,
                description=f"{slot.role or roleIdentity.value} ({profileName})",
            )
            profileCache[profileKey] = roleProfile

        return Position(
            identity=identity,
            role=role,
            roleProfile=roleProfile,
        )

    def _slotSortKey(self, slot: StructuredFormationSlot) -> tuple[int, str]:
        """Sort slots by semantic position ordering for stable rendering flow."""

        identity = self._positionIdentityParse(slot.position)
        if identity is None:
            return len(self._POSITION_ORDER), slot.slotId
        return self._POSITION_ORDER[identity], slot.slotId

    def _slotsForPhase(
        self,
        definition: StructuredTacticDefinition,
        phase: str,
    ) -> list[StructuredFormationSlot]:
        """Collect and return slots for one exact stored phase name."""

        return [slot for slot in definition.slots if slot.phase == phase]

    ## instructions

    def _instructionCatalogBuild(
        self,
        definition: StructuredTacticDefinition,
    ) -> dict[str, Instruction]:
        """Build one instruction object per category with all observed values.

        This keeps instruction objects reusable across formations and transition,
        which aligns with the object-model concept that each instruction is unique.
        """

        valueMap: dict[str, list[InstructionValue]] = {}
        for stored in definition.instructions:
            instructionName = stored.category.strip() or "unknown"
            bucket = valueMap.setdefault(instructionName, [])
            value = InstructionValue(
                name=self._valueToText(stored.canonicalValue)
                or stored.displayValue.strip()
                or "unknown",
                description=stored.displayValue.strip(),
            )
            if value not in bucket:
                bucket.append(value)

        return {
            name: Instruction(name=name, values=tuple(values))
            for name, values in sorted(valueMap.items(), key=lambda item: item[0].casefold())
        }

    def _instructionsBuild(
        self,
        definition: StructuredTacticDefinition,
        instructionCatalog: dict[str, Instruction],
        phase: str,
    ) -> InstructionSet:
        """Build one instruction set keyed by canonical category."""

        byCategory: dict[str, tuple[float, str, InstructionValue]] = {}
        for stored in definition.instructions:
            if stored.phase != phase:
                continue

            instructionName = stored.category.strip() or "unknown"
            instruction = instructionCatalog.get(instructionName)
            if instruction is None:
                continue
            value = self._instructionValueFind(stored, instruction)
            if value is None:
                continue

            current = byCategory.get(instructionName)
            if current is None or stored.confidence >= current[0]:
                byCategory[instructionName] = (stored.confidence, instructionName, value)

        return {
            instructionCatalog[name]: value
            for _, name, value in sorted(byCategory.values(), key=lambda item: item[1].casefold())
        }

    def _instructionValueFind(
        self,
        stored: StructuredTeamInstruction,
        instruction: Instruction,
    ) -> InstructionValue | None:
        """Select an existing instruction value from the instruction catalog."""

        targetName = self._valueToText(stored.canonicalValue)
        targetDisplay = stored.displayValue.strip()
        for value in instruction.values:
            if targetName and value.name == targetName:
                return value
            if targetDisplay and value.description == targetDisplay:
                return value
        return None

    def _transitionBuild(
        self,
        definition: StructuredTacticDefinition,
        instructionCatalog: dict[str, Instruction],
        issues: list[TacticBuildIssue],
    ) -> Transition:
        """Build transition instructions from dedicated or legacy phase names."""

        instructions = self._instructionsBuild(definition, instructionCatalog, "transition")
        if instructions:
            return Transition(instructions=instructions)

        # Some stored data sets still persist transition categories under
        # in-possession phase names; preserve usability by falling back.
        fallback = {
            instruction: value
            for instruction, value in self._instructionsBuild(
                definition,
                instructionCatalog,
                "inPossession",
            ).items()
            if instruction.name.casefold()
            in {
                "possessionlost",
                "possessionwon",
                "when possession has been lost",
                "when possession has been won",
            }
        }
        if fallback:
            issues.append(
                TacticBuildIssue(
                    "transitionFallback",
                    "Transition instructions were inferred from in-possession categories",
                )
            )
        return Transition(instructions=fallback)

    ## identity

    def _positionIdentityParse(self, value: str | None) -> PositionIdentity | None:
        """Map stored position text to a known PositionIdentity."""

        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized:
            return None
        try:
            return PositionIdentity[normalized]
        except KeyError:
            return None

    def _roleIdentityParse(
        self,
        roleCode: str | None,
        observedRole: str,
    ) -> RoleIdentity | None:
        """Map canonical or observed role text to a known RoleIdentity."""

        return RoleVocabulary.identityResolve(roleCode or "", observedRole)

    def _valueToText(self, value: str | bool | None) -> str:
        """Convert JSON-typed canonical values to a stable object-model label."""

        if value is None:
            return ""
        if isinstance(value, bool):
            return "enabled" if value else "disabled"
        return str(value).strip()
