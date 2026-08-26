"""Role-level, explainable squad assessment independent from Qt."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from fmsat.core.builder.tacticModelLoader import TacticModelLoader
from fmsat.core.parser import TacticVocabulary
from fmsat.core.roleDepth import RequiredSlotAssessment, RoleDepthService
from fmsat.core.roleKnowledge import RoleKnowledgeService, StoredRoleDefinition
from fmsat.core.rolePositionCompatibility import RolePositionFamilyPolicy
from fmsat.core.squadModel import SquadModel, SquadModelPlayer, SquadModelService
from fmsat.database import Database
from fmsat.tactics.position import Position
from fmsat.tactics.positionFamily import positionFamilyFor


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
class PlayerRoleFit:
    """One named role and score used in a player's role ordering."""

    roleCode: str
    displayName: str
    score: float


@dataclass(frozen=True, slots=True)
class PlayerRoleAssessment:
    """One player's best and alternative roles from the complete role catalogue."""

    player: SquadModelPlayer
    bestRole: PlayerRoleFit | None
    alternativeRoles: tuple[PlayerRoleFit, ...]
    unavailableReason: str | None


@dataclass(frozen=True, slots=True)
class AnalysisFinding:
    """One deterministic squad-level observation backed by Generic Role Fit."""

    code: str
    title: str
    explanation: str


@dataclass(frozen=True, slots=True)
class SquadAssessment:
    """UI-independent assessment result for one squad and tactic context."""

    squad: SquadModel
    tacticName: str | None
    availableTactics: tuple[str, ...]
    requiredPositionCount: int
    roles: tuple[RequiredRoleAssessment, ...]
    scoringIdentity: str = "Unavailable"
    allRoles: tuple[RequiredRoleAssessment, ...] = field(default_factory=tuple)
    players: tuple[PlayerRoleAssessment, ...] = field(default_factory=tuple)
    weakRoles: tuple[AnalysisFinding, ...] = field(default_factory=tuple)
    duplicatedRoles: tuple[AnalysisFinding, ...] = field(default_factory=tuple)
    unusedStrengths: tuple[AnalysisFinding, ...] = field(default_factory=tuple)
    requiredSlots: tuple[RequiredSlotAssessment, ...] = field(default_factory=tuple)


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
        missing = sorted(attribute for attribute in activeWeights if values.get(attribute) is None)
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
        self.positionFamilies = RolePositionFamilyPolicy.load()
        self.calculator = calculator or GenericRoleFitCalculator()
        candidateSettings = getattr(roleKnowledge, "assessmentSettings", {})
        settings = candidateSettings if isinstance(candidateSettings, Mapping) else {}
        self.scoringIdentity = str(settings.get("identity", "Unavailable"))
        self.weakRoleFitThreshold = float(settings.get("weakRoleFitThreshold", 60.0))
        self.duplicationFitThreshold = float(settings.get("duplicationFitThreshold", 60.0))
        self.duplicationMinimumPlayers = int(settings.get("duplicationMinimumPlayers", 3))
        self.unusedStrengthThreshold = float(settings.get("unusedStrengthThreshold", 60.0))
        self.alternativeRoleLimit = int(settings.get("alternativeRoleLimit", 3))
        self.slotAggregationPolicy = str(settings.get("slotAggregationPolicy", "Unavailable"))

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
        definitions = self._definitionsByCode()
        allRoles = self._allRolesAssess(squad, definitions)
        catalogueByCode = {role.roleCode: role for role in allRoles}
        players = self._playersAssess(squad, allRoles)
        selectedTactic = tacticName if tacticName in availableTactics else None
        if selectedTactic is None and availableTactics:
            selectedTactic = availableTactics[0]
        if selectedTactic is None:
            return SquadAssessment(
                squad,
                None,
                availableTactics,
                0,
                (),
                self.scoringIdentity,
                allRoles,
                players,
            )

        loaded = self.tacticModels.tacticLoad(selectedTactic)
        if loaded.tactic is None:
            return SquadAssessment(
                squad,
                selectedTactic,
                availableTactics,
                0,
                (),
                self.scoringIdentity,
                allRoles,
                players,
            )

        # A tactic can use the same canonical role in several positions and phases.
        # Retain the formation size separately while assessing each role identity once.
        requiredPositionCount = max(
            len(loaded.tactic.inPossession.positions),
            len(loaded.tactic.outOfPossession.positions),
        )
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
                exactPosition = position.canonicalPosition or position.identity.value
                family = positionFamilyFor(exactPosition)
                context["positions"].add(family.value if family is not None else exactPosition)
                context["phases"].add(phase)

        roles = tuple(
            replace(
                catalogueByCode.get(roleCode)
                or self._roleAssess(roleCode, set(), set(), squad, definitions.get(roleCode)),
                positions=tuple(sorted(required[roleCode]["positions"])),
                phases=tuple(sorted(required[roleCode]["phases"])),
            )
            for roleCode in sorted(
                required,
                key=lambda code: self._roleSortKey(code, definitions.get(code)),
            )
        )
        requiredSlots = RoleDepthService(self.slotAggregationPolicy).depthBuild(
            loaded.tactic,
            catalogueByCode,
        )
        return SquadAssessment(
            squad=squad,
            tacticName=selectedTactic,
            availableTactics=availableTactics,
            requiredPositionCount=requiredPositionCount,
            roles=roles,
            scoringIdentity=self.scoringIdentity,
            allRoles=allRoles,
            players=players,
            weakRoles=self._weakRolesFind(roles),
            duplicatedRoles=self._duplicatedRolesFind(roles, players),
            unusedStrengths=self._unusedStrengthsFind(roles, players),
            requiredSlots=requiredSlots,
        )

    ## analysis

    def _duplicatedRolesFind(
        self,
        roles: tuple[RequiredRoleAssessment, ...],
        players: tuple[PlayerRoleAssessment, ...],
    ) -> tuple[AnalysisFinding, ...]:
        """Identify several strong players whose best role is the same required role."""

        requiredCodes = {role.roleCode for role in roles}
        grouped: dict[str, list[PlayerRoleAssessment]] = {}
        for player in players:
            best = player.bestRole
            if (
                best is not None
                and best.roleCode in requiredCodes
                and best.score >= self.duplicationFitThreshold
            ):
                grouped.setdefault(best.roleCode, []).append(player)
        findings = []
        roleNames = {role.roleCode: role.displayName for role in roles}
        for roleCode, candidates in sorted(grouped.items()):
            if len(candidates) < self.duplicationMinimumPlayers:
                continue
            names = ", ".join(player.player.name for player in candidates)
            findings.append(
                AnalysisFinding(
                    roleCode,
                    roleNames[roleCode],
                    f"{len(candidates)} players have this as their best role at "
                    f"{self.duplicationFitThreshold:.1f} or above: {names}.",
                )
            )
        return tuple(findings)

    def _playersAssess(
        self,
        squad: SquadModel,
        roles: tuple[RequiredRoleAssessment, ...],
    ) -> tuple[PlayerRoleAssessment, ...]:
        """Order every calculable catalogue role for every available player."""

        results = []
        for player in squad.players:
            available = sorted(
                (
                    PlayerRoleFit(role.roleCode, role.displayName, candidate.genericRoleFit.score)
                    for role in roles
                    for candidate in role.candidates
                    if candidate.player is player and candidate.genericRoleFit.score is not None
                ),
                key=lambda fit: (-fit.score, fit.displayName.casefold()),
            )
            results.append(
                PlayerRoleAssessment(
                    player,
                    available[0] if available else None,
                    tuple(available[1 : 1 + self.alternativeRoleLimit]),
                    None if available else "No role has complete attributes and weights",
                )
            )
        return tuple(sorted(results, key=lambda item: item.player.name.casefold()))

    def _unusedStrengthsFind(
        self,
        roles: tuple[RequiredRoleAssessment, ...],
        players: tuple[PlayerRoleAssessment, ...],
    ) -> tuple[AnalysisFinding, ...]:
        """Identify strong best roles which the selected tactic does not use."""

        requiredCodes = {role.roleCode for role in roles}
        return tuple(
            AnalysisFinding(
                player.player.name,
                player.player.name,
                f"Best role is {player.bestRole.displayName} at {player.bestRole.score:.1f}, "
                "but that role is not used by the selected tactic.",
            )
            for player in players
            if player.bestRole is not None
            and player.bestRole.roleCode not in requiredCodes
            and player.bestRole.score >= self.unusedStrengthThreshold
        )

    def _weakRolesFind(
        self,
        roles: tuple[RequiredRoleAssessment, ...],
    ) -> tuple[AnalysisFinding, ...]:
        """Identify unavailable, single-candidate or below-threshold role coverage."""

        findings = []
        for role in roles:
            available = [
                candidate
                for candidate in role.candidates
                if candidate.genericRoleFit.score is not None
            ]
            suitable = [
                candidate
                for candidate in available
                if candidate.genericRoleFit.score >= self.weakRoleFitThreshold
            ]
            if not available:
                explanation = "No player has complete evidence for a calculable score."
            elif not suitable:
                explanation = (
                    f"Best fit is {available[0].player.name} at "
                    f"{available[0].genericRoleFit.score:.1f}, below the "
                    f"{self.weakRoleFitThreshold:.1f} threshold."
                )
            elif len(suitable) == 1:
                explanation = (
                    f"{suitable[0].player.name} is the only candidate at "
                    f"{self.weakRoleFitThreshold:.1f} or above."
                )
            else:
                continue
            findings.append(AnalysisFinding(role.roleCode, role.displayName, explanation))
        return tuple(findings)

    ## catalogue

    def _allRolesAssess(
        self,
        squad: SquadModel,
        definitions: dict[str, StoredRoleDefinition],
    ) -> tuple[RequiredRoleAssessment, ...]:
        """Assess packaged and user-confirmed semantic roles as one complete catalogue."""

        roleCodes = set(self.vocabulary.roles) | set(definitions)
        return tuple(
            self._roleAssess(
                roleCode,
                self._rolePositionFamilies(roleCode, definitions.get(roleCode)),
                set(),
                squad,
                definitions.get(roleCode),
            )
            for roleCode in sorted(
                roleCodes,
                key=lambda code: self._roleSortKey(code, definitions.get(code)),
            )
        )

    def _rolePositionFamilies(
        self,
        roleCode: str,
        definition: StoredRoleDefinition | None,
    ) -> set[str]:
        """Return explicit family compatibility, preserving unknown custom evidence."""

        configured = self.positionFamilies.familiesFor(roleCode)
        if configured:
            return {family.value for family in configured}
        if definition is None:
            return set()
        result: set[str] = set()
        for position in definition.positions:
            family = positionFamilyFor(position)
            result.add(family.value if family is not None else position)
        return result

    ## roles

    def _canonicalRoleResolve(self, position: Position) -> str | None:
        """Resolve exact semantic role identity while preserving confirmed custom roles."""

        canonical = str(position.canonicalRole or "").strip()
        if canonical:
            normalized = self.vocabulary.roleNormalize(canonical)
            if getattr(normalized, "resolved", False) is True:
                return str(normalized.value)
            exactPosition = str(
                getattr(position, "canonicalPosition", None)
                or getattr(getattr(position, "identity", None), "value", "")
                or ""
            ).strip()
            if canonical.casefold() != exactPosition.casefold():
                return canonical
            # A legacy position value in canonicalRole is not semantic role
            # evidence.  Ignore it and continue to the observed role profile,
            # which can still recover AM -> attackingMidfielder, for example.

        observed = position.roleProfile.description.split(" (", 1)[0].strip()
        normalized = self.vocabulary.roleNormalize(observed)
        if getattr(normalized, "resolved", False) is True:
            return str(normalized.value)

        folded = observed.casefold()
        matches = [
            definition.roleCode
            for definition in self.roleKnowledge.definitionsList()
            if definition.displayName.casefold() == folded
            or any(abbreviation.casefold() == folded for abbreviation in definition.abbreviations)
        ]
        return matches[0] if len(matches) == 1 else None

    def _definitionsByCode(self) -> dict[str, StoredRoleDefinition]:
        """Return confirmed definitions keyed by their stable canonical role code."""

        return {
            definition.roleCode: definition for definition in self.roleKnowledge.definitionsList()
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
        weights = self.roleKnowledge.weightsLoad(roleCode)
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

        positions = self._rolePositionFamilies(roleCode, definition)
        ranks = []
        for position in positions:
            if position == "STC":
                ranks.append(0)
            elif position in {"AMC", "AMW"}:
                ranks.append(1)
            elif position in {"MC", "MW"}:
                ranks.append(2)
            elif position == "DM":
                ranks.append(3)
            elif position in {"FB", "WB", "DC"}:
                ranks.append(4)
            elif position == "GK":
                ranks.append(5)
        return min(ranks, default=6), roleCode.casefold()
