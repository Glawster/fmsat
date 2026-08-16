"""Build football object-model tactics from persisted structured DB data."""

from __future__ import annotations

from dataclasses import dataclass

from fmsat.core.logUtils import getLogger
from fmsat.database.models import (
    StructuredFormationSlot,
    ScreenshotDerivedTacticDefinition,
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

logger = getLogger()


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
    """Load a persisted tactic and translate it into the football object model."""

    _POSITION_ORDER = {identity: index for index, identity in enumerate(PositionIdentity)}

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    ## tactic

    def tacticBuild(self, tacticName: str) -> TacticBuildResult:
        """Build one football-model tactic from the database by tactic name."""

        issues: list[TacticBuildIssue] = []
        cleanName = tacticName.strip()
        logger.doing(f"building tactic object model for {cleanName or '<empty>'}")
        if not cleanName:
            issues.append(TacticBuildIssue("invalidTacticName", "Tactic name is empty"))
            return TacticBuildResult(None, tuple(issues), False, False)

        with Session(self.engine) as session:
            definition = self._definitionLoad(session, cleanName)

        if definition is None:
            issues.append(TacticBuildIssue(
                "missingStructuredDefinition",
                f"No screenshot-derived tactic definition exists for {cleanName!r}",
            ))
            return TacticBuildResult(None, tuple(issues), False, False)

        issues.extend(TacticBuildIssue(issue.code, issue.message) for issue in definition.issues)
        inPossessionSlots = self._slotsForPhase(definition, "inPossession")
        outOfPossessionSlots = self._slotsForPhase(definition, "outOfPossession")
        instructionCatalog = self._instructionCatalogBuild(definition)

        # FMSAT owns tactic identity. Football Manager's template/shape label is
        # not a formation identity, so both phase names are deterministically
        # derived from the user-owned tactic name.
        inPossessionModel = self._formationBuild(
            formationName=f"{cleanName} IP",
            slots=inPossessionSlots,
            definition=definition,
            instructionCatalog=instructionCatalog,
            phaseName="inPossession",
            issues=issues,
        )
        outOfPossessionModel = self._formationBuild(
            formationName=f"{cleanName} OOP",
            slots=outOfPossessionSlots,
            definition=definition,
            instructionCatalog=instructionCatalog,
            phaseName="outOfPossession",
            issues=issues,
        )
        transitionModel = self._transitionBuild(definition, instructionCatalog, issues)

        if inPossessionModel is None or outOfPossessionModel is None:
            return TacticBuildResult(None, tuple(issues), definition.complete, definition.confirmed)

        tacticModel = Tactic(
            name=cleanName,
            inPossession=inPossessionModel,
            outOfPossession=outOfPossessionModel,
            transition=transitionModel,
        )
        return TacticBuildResult(tacticModel, tuple(issues), definition.complete, definition.confirmed)

    ## definition

    def _definitionLoad(self, session: Session, tacticName: str) -> ScreenshotDerivedTacticDefinition | None:
        query: Select[tuple[DatabaseTactic]] = (
            select(DatabaseTactic)
            .where(DatabaseTactic.normalizedName == tacticName.casefold())
            .options(
                selectinload(DatabaseTactic.structuredDefinition).selectinload(ScreenshotDerivedTacticDefinition.slots),
                selectinload(DatabaseTactic.structuredDefinition).selectinload(ScreenshotDerivedTacticDefinition.instructions),
                selectinload(DatabaseTactic.structuredDefinition).selectinload(ScreenshotDerivedTacticDefinition.issues),
            )
        )
        record = session.scalar(query)
        return record.structuredDefinition if record is not None else None

    ## formation

    def _formationBuild(self, formationName: str, slots: list[StructuredFormationSlot], definition: ScreenshotDerivedTacticDefinition, instructionCatalog: dict[str, Instruction], phaseName: str, issues: list[TacticBuildIssue]) -> Formation | None:
        positions: list[Position] = []
        roleCache: dict[RoleIdentity, Role] = {}
        profileCache: dict[tuple[RoleIdentity, str], RoleProfile] = {}
        for slot in sorted(slots, key=self._slotSortKey):
            position = self._positionBuild(slot, phaseName, issues, roleCache, profileCache)
            if position is not None:
                positions.append(position)
        if not positions:
            issues.append(TacticBuildIssue("emptyFormation", f"No valid {phaseName} positions could be mapped into the object model"))
            return None
        if len(positions) < 11:
            issues.append(TacticBuildIssue("incompleteFormation", f"{phaseName} has {len(positions)} mapped positions; 11 expected"))
        return Formation(name=formationName, positions=positions, instructions=self._instructionsBuild(definition, instructionCatalog, phaseName))

    def _positionBuild(self, slot: StructuredFormationSlot, phaseName: str, issues: list[TacticBuildIssue], roleCache: dict[RoleIdentity, Role], profileCache: dict[tuple[RoleIdentity, str], RoleProfile]) -> Position | None:
        identity = self._positionIdentityParse(slot.position)
        if identity is None:
            issues.append(TacticBuildIssue("unknownPositionIdentity", f"{phaseName} slot {slot.slotId!r} has unknown position {slot.position!r}"))
            return None
        roleIdentity = self._roleIdentityParse(slot.role, slot.observedRole)
        if roleIdentity is None:
            if slot.observedRole:
                roleIdentity = RoleIdentity.UNRESOLVED
                issues.append(TacticBuildIssue("roleDefinitionRequired", f"{phaseName} slot {slot.slotId!r} retains observed role {slot.observedRole!r}; a user definition is required"))
            else:
                issues.append(TacticBuildIssue("unknownRoleIdentity", f"{phaseName} slot {slot.slotId!r} has no recognizable role evidence"))
                return None
        role = roleCache.get(roleIdentity)
        if role is None:
            role = Role(identity=roleIdentity)
            roleCache[roleIdentity] = role
        profileKey = (roleIdentity, slot.observedRole if roleIdentity is RoleIdentity.UNRESOLVED else slot.duty or "__not_shown__")
        roleProfile = profileCache.get(profileKey)
        if roleProfile is None:
            profileName = slot.observedRole if roleIdentity is RoleIdentity.UNRESOLVED or (slot.role or "").startswith("capturedRole") else slot.duty.capitalize() if slot.duty else "Observed role"
            roleProfile = RoleProfile(name=profileName, description=f"{slot.observedRole or slot.role or roleIdentity.value} ({profileName})")
            profileCache[profileKey] = roleProfile
        return Position(identity=identity, role=role, roleProfile=roleProfile, canonicalPosition=slot.position, canonicalRole=slot.role, slotId=slot.slotId, duty=slot.duty, x=slot.x, y=slot.y, player=None, confidence=slot.confidence, sourceImportSessionId=slot.sourceImportSessionId, validationState=slot.validationState)

    def _slotSortKey(self, slot: StructuredFormationSlot) -> tuple[int, str]:
        identity = self._positionIdentityParse(slot.position)
        return (len(self._POSITION_ORDER), slot.slotId) if identity is None else (self._POSITION_ORDER[identity], slot.slotId)

    def _slotsForPhase(self, definition: ScreenshotDerivedTacticDefinition, phase: str) -> list[StructuredFormationSlot]:
        return [slot for slot in definition.slots if slot.phase == phase]

    ## instructions

    def _instructionCatalogBuild(self, definition: ScreenshotDerivedTacticDefinition) -> dict[str, Instruction]:
        valueMap: dict[str, list[InstructionValue]] = {}
        for stored in definition.instructions:
            instructionName = stored.category.strip() or "unknown"
            bucket = valueMap.setdefault(instructionName, [])
            value = InstructionValue(name=self._valueToText(stored.canonicalValue) or stored.displayValue.strip() or "unknown", description=stored.displayValue.strip())
            if value not in bucket:
                bucket.append(value)
        return {name: Instruction(name=name, values=tuple(values)) for name, values in sorted(valueMap.items(), key=lambda item: item[0].casefold())}

    def _instructionsBuild(self, definition: ScreenshotDerivedTacticDefinition, instructionCatalog: dict[str, Instruction], phase: str) -> InstructionSet:
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
        return {instructionCatalog[name]: value for _, name, value in sorted(byCategory.values(), key=lambda item: item[1].casefold())}

    def _instructionValueFind(self, stored: StructuredTeamInstruction, instruction: Instruction) -> InstructionValue | None:
        targetName = self._valueToText(stored.canonicalValue)
        targetDisplay = stored.displayValue.strip()
        for value in instruction.values:
            if targetName and value.name == targetName:
                return value
            if targetDisplay and value.description == targetDisplay:
                return value
        return None

    def _transitionBuild(self, definition: ScreenshotDerivedTacticDefinition, instructionCatalog: dict[str, Instruction], issues: list[TacticBuildIssue]) -> Transition:
        instructions = self._instructionsBuild(definition, instructionCatalog, "transition")
        if instructions:
            return Transition(instructions=instructions)
        fallback = {instruction: value for instruction, value in self._instructionsBuild(definition, instructionCatalog, "inPossession").items() if instruction.name.casefold() in {"possessionlost", "possessionwon", "when possession has been lost", "when possession has been won"}}
        if fallback:
            issues.append(TacticBuildIssue("transitionFallback", "Transition instructions were inferred from in-possession categories"))
        return Transition(instructions=fallback)

    ## identity

    def _positionIdentityParse(self, value: str | None) -> PositionIdentity | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        canonicalToDomain = {"DCL": "DC", "DCR": "DC", "DMCL": "DM", "DMCR": "DM", "MCL": "MC", "MCR": "MC", "AMCL": "AMC", "AMCR": "AMC", "STCL": "ST", "STC": "ST", "STCR": "ST"}
        normalized = canonicalToDomain.get(normalized, normalized)
        try:
            return PositionIdentity[normalized]
        except KeyError:
            return None

    def _roleIdentityParse(self, roleCode: str | None, observedRole: str) -> RoleIdentity | None:
        for candidate in (roleCode, observedRole):
            if not candidate:
                continue
            mapped = RoleVocabulary.identityFor(candidate)
            if mapped is not None:
                return mapped
            normalized = candidate.strip().replace(" ", "").replace("-", "").casefold()
            for identity in RoleIdentity:
                if identity.value.replace("_", "").casefold() == normalized or identity.name.replace("_", "").casefold() == normalized:
                    return identity
        return None

    @staticmethod
    def _valueToText(value: object) -> str:
        if value is None:
            return ""
        raw = getattr(value, "value", value)
        return raw.strip() if isinstance(raw, str) else str(raw).strip()
