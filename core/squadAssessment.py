"""Role-level, explainable squad assessment independent from Qt."""

from __future__ import annotations

from dataclasses import dataclass

from fmsat.core.builder.tacticModelLoader import TacticModelLoader
from fmsat.core.parser import TacticVocabulary
from fmsat.core.roleKnowledge import RoleKnowledgeService, StoredRoleDefinition
from fmsat.core.squadModel import SquadModel, SquadModelPlayer, SquadModelService
from fmsat.database import Database
from fmsat.tactics.position import Position


@dataclass(frozen=True, slots=True)
class AttributeContribution:
    """One transparent weighted attribute contribution."""

    attribute: str
    value: int
    weight: int
    weightedPoints: int
    maximumPoints: int


@dataclass(frozen=True, slots=True)
class GenericRoleFit:
    """Available or explicitly unavailable Generic Role Fit."""

    score: float | None
    unavailableReason: str | None
    contributions: tuple[AttributeContribution, ...]

    @property
    def available(self) -> bool:
        """Return whether a reproducible score was calculated."""

        return self.score is not None


@dataclass(frozen=True, slots=True)
class RoleCandidate:
    """One squad player assessed against one canonical role."""

    player: SquadModelPlayer
    genericRoleFit: GenericRoleFit


@dataclass(frozen=True, slots=True)
class RequiredRoleAssessment:
    """One unique canonical tactic role and all squad candidates for it."""

    roleCode: str
    roleID: int | None
    displayName: str
    abbreviation: str
    positions: tuple[str, ...]
    phases: tuple[str, ...]
    candidates: tuple[RoleCandidate, ...]
    bestCandidate: str | None
    backupCandidate: str | None
    uncovered: bool


@dataclass(frozen=True, slots=True)
class SquadAssessment:
    """UI-independent assessment result for one squad and tactic context."""

    squad: SquadModel
    tacticName: str | None
    availableTactics: tuple[str, ...]
    requiredPositionCount: int
    roles: tuple[RequiredRoleAssessment, ...]


class GenericRoleFitCalculator:
    """Calculate one normalized 0–100 score from explicit 0–5 role weights."""

    def calculate(
        self,
        player: SquadModelPlayer,
        weights: dict[str, int],
    ) -> GenericRoleFit:
        """Return an explainable score, or why one cannot safely be calculated."""

        activeWeights = {
            attribute: weight
            for attribute, weight in weights.items()
            if isinstance(weight, int) and weight > 0
        }
        if not activeWeights:
            return GenericRoleFit(None, "No assessment weights are defined", ())

        values = dict(player.attributes)
        missing = sorted(
            attribute
            for attribute in activeWeights
            if values.get(attribute) is None
        )
        if missing:
            return GenericRoleFit(
                None,
                "Missing attributes: " + ", ".join(missing),
                (),
            )

        contributions = tuple(
            AttributeContribution(
                attribute=attribute,
                value=int(values[attribute]),
                weight=weight,
                weightedPoints=int(values[attribute]) * weight,
                maximumPoints=20 * weight,
            )
            for attribute, weight in sorted(activeWeights.items())
        )
        earned = sum(item.weightedPoints for item in contributions)
        maximum = sum(item.maximumPoints for item in contributions)
        return GenericRoleFit(
            score=round((earned / maximum) * 100, 1),
            unavailableReason=None,
            contributions=contributions,
        )


class SquadAssessmentService:
    """Load model inputs and produce role-level assessment view data."""

    def __init__(
        self,
        database: Database,
        squadModels: SquadModelService,
        tacticModels: TacticModelLoader,
        roleKnowledge: RoleKnowledgeService,
        vocabulary: TacticVocabulary,
        calculator: GenericRoleFitCalculator | None = None,
    ) -> None:
        self.database = database
        self.squadModels = squadModels
        self.tacticModels = tacticModels
        self.roleKnowledge = roleKnowledge
        self.vocabulary = vocabulary
        self.calculator = calculator or GenericRoleFitCalculator()

    ## assessment

    def assessmentBuild(
        self,
        squadName: str,
        tacticName: str | None = None,
    ) -> SquadAssessment | None:
        """Build one assessment without allowing position to replace role identity."""

        squad = self.squadModels.modelLoad(squadName)
        if squad is None:
            return None
        availableTactics = self.database.squadAppliedTactics(squadName)
        selectedTactic = tacticName if tacticName in availableTactics else None
        if selectedTactic is None and availableTactics:
            selectedTactic = availableTactics[0]
        if selectedTactic is None:
            return SquadAssessment(squad, None, availableTactics, 0, ())

        loaded = self.tacticModels.tacticLoad(selectedTactic)
        if loaded.tactic is None:
            return SquadAssessment(squad, selectedTactic, availableTactics, 0, ())

        # A tactic can use the same canonical role in several positions and phases.
        # Retain the formation size separately while assessing each role identity once.
        requiredPositionCount = max(
            len(loaded.tactic.inPossession.positions),
            len(loaded.tactic.outOfPossession.positions),
        )
        definitions = self._definitionsByCode()
        required: dict[str, dict[str, set[str]]] = {}
        for phase, formation in (
            ("In Possession", loaded.tactic.inPossession),
            ("Out Of Possession", loaded.tactic.outOfPossession),
        ):
            for position in formation.positions:
                roleCode = self._canonicalRoleResolve(position)
                if roleCode is None:
                    continue
                context = required.setdefault(
                    roleCode,
                    {"positions": set(), "phases": set()},
                )
                context["positions"].add(
                    position.canonicalPosition or position.identity.value
                )
                context["phases"].add(phase)

        roles = tuple(
            self._roleAssess(
                roleCode,
                required[roleCode]["positions"],
                required[roleCode]["phases"],
                squad,
                definitions.get(roleCode),
            )
            for roleCode in sorted(
                required,
                key=lambda code: self._roleSortKey(code, definitions.get(code)),
            )
        )
        return SquadAssessment(
            squad,
            selectedTactic,
            availableTactics,
            requiredPositionCount,
            roles,
        )

    ## roles

    def _canonicalRoleResolve(self, position: Position) -> str | None:
        """Resolve the exact Football Manager role, never its broad position domain."""

        if position.canonicalRole:
            return position.canonicalRole
        observed = position.roleProfile.description.split(" (", 1)[0].strip()
        normalized = self.vocabulary.roleNormalize(observed)
        return normalized.value if normalized.resolved else None

    def _definitionsByCode(self) -> dict[str, StoredRoleDefinition]:
        """Return confirmed definitions keyed by their stable canonical role code."""

        return {
            definition.roleCode: definition
            for definition in self.roleKnowledge.definitionsList()
            if definition.roleCode is not None
        }

    def _roleAssess(
        self,
        roleCode: str,
        positions: set[str],
        phases: set[str],
        squad: SquadModel,
        storedDefinition: StoredRoleDefinition | None,
    ) -> RequiredRoleAssessment:
        """Assess every player against one role and calculate simple coverage."""

        vocabularyRole = self.vocabulary.roles.get(roleCode)
        roleID = (
            vocabularyRole.roleID
            if vocabularyRole is not None
            else storedDefinition.roleID if storedDefinition is not None else None
        )
        displayName = (
            vocabularyRole.displayName
            if vocabularyRole is not None
            else storedDefinition.displayName if storedDefinition is not None else roleCode
        )
        abbreviations = (
            storedDefinition.abbreviations
            if storedDefinition is not None and storedDefinition.abbreviations
            else vocabularyRole.abbreviations if vocabularyRole is not None else ()
        )
        weights = self.roleKnowledge.weightsLoad(roleID) if roleID is not None else {}
        candidates = tuple(
            sorted(
                (
                    RoleCandidate(player, self.calculator.calculate(player, weights))
                    for player in squad.players
                ),
                key=lambda candidate: (
                    not candidate.genericRoleFit.available,
                    -(
                        candidate.genericRoleFit.score
                        if candidate.genericRoleFit.score is not None
                        else -1.0
                    ),
                    candidate.player.name.casefold(),
                ),
            )
        )
        available = [candidate for candidate in candidates if candidate.genericRoleFit.available]
        return RequiredRoleAssessment(
            roleCode=roleCode,
            roleID=roleID,
            displayName=displayName,
            abbreviation=abbreviations[0] if abbreviations else roleCode,
            positions=tuple(sorted(positions)),
            phases=tuple(sorted(phases)),
            candidates=candidates,
            bestCandidate=available[0].player.name if available else None,
            backupCandidate=available[1].player.name if len(available) > 1 else None,
            uncovered=not available,
        )

    def _roleSortKey(
        self,
        roleCode: str,
        definition: StoredRoleDefinition | None,
    ) -> tuple[int, str]:
        """Order unique roles by their highest supported tactical line."""

        role = self.vocabulary.roles.get(roleCode)
        positions = (
            role.positions
            if role is not None
            else definition.positions
            if definition is not None
            else ()
        )
        ranks = []
        for position in positions:
            if position.startswith("ST"):
                ranks.append(0)
            elif position.startswith("AM"):
                ranks.append(1)
            elif position.startswith("M"):
                ranks.append(2)
            elif position.startswith("DM"):
                ranks.append(3)
            elif position.startswith("D") or position.startswith("WB"):
                ranks.append(4)
            elif position == "GK":
                ranks.append(5)
        return min(ranks, default=6), roleCode.casefold()
