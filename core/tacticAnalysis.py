"""Squad-independent tactic demand built from pairing, roles, and assessment policy.

Tactic Analysis answers what a saved tactic demands. It does not assign players,
score Generic Role Fit, or import Qt. Missing evidence stays Unavailable.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal, Mapping

from fmsat.core.config import AttributeDefinition
from fmsat.core.parser import TacticVocabulary
from fmsat.core.roleKnowledge import RoleKnowledgeService, StoredRoleDefinition
from fmsat.core.tacticSlots import LinkedTacticSlot, slotSortKey, slotsLink
from fmsat.tactics.positionFamily import positionFamilyFor

PhaseName = Literal["IP", "OOP"]
ResolutionState = Literal[
    "missingPhase",
    "unresolved",
    "recognitionOnly",
    "missingWeights",
    "ready",
]
TransitionClass = Literal[
    "unavailable",
    "unchanged",
    "roleChangeSameFamily",
    "familyChange",
]
ObservationCode = Literal[
    "repeatedRole",
    "asymmetricFlank",
    "trackingRoleCount",
    "familyChangeCount",
    "demandConcentration",
]

# Packaged Tracking identities. Update this set in the same change as any new
# packaged Tracking vocabulary entry. Do not infer membership from a prefix.
TRACKING_ROLE_CODES = frozenset(
    {
        "trackingCentreForward",
        "trackingAttackingMidfielder",
        "trackingWideMidfielder",
        "trackingWinger",
    }
)

# Exact L/R pairs already present in positionFamilyFor. Central codes never pair.
_FLANK_PAIRS = (
    ("DL", "DR"),
    ("DCL", "DCR"),
    ("WBL", "WBR"),
    ("DMCL", "DMCR"),
    ("MCL", "MCR"),
    ("ML", "MR"),
    ("AMCL", "AMCR"),
    ("AML", "AMR"),
    ("STCL", "STCR"),
)

# Demand uses the packaged assessment scale (currently 0-10 after 007D).
# Stored 0 is an omitted attribute, matching Generic Role Fit, not a demand of 0.
_WEIGHT_MINIMUM = 0
_WEIGHT_MAXIMUM = 10


@dataclass(frozen=True, slots=True)
class TacticPhaseRole:
    """One phase-role on one simultaneous slot, with its evidence state."""

    phase: PhaseName
    roleCode: str | None
    displayName: str
    abbreviation: str
    canonicalPosition: str
    resolutionState: ResolutionState
    weights: dict[str, int] | None
    unavailableReason: str | None


@dataclass(frozen=True, slots=True)
class PhaseTransition:
    """IP→OOP classification for one linked slot, or Unavailable."""

    classification: TransitionClass
    ipFamily: str | None
    oopFamily: str | None
    explanation: str


@dataclass(frozen=True, slots=True)
class TacticSlotDemand:
    """Demand and structure for one simultaneous tactic slot."""

    slotId: str
    canonicalPosition: str
    ipRole: TacticPhaseRole
    oopRole: TacticPhaseRole
    transition: PhaseTransition
    linkageUnavailableReason: str | None


@dataclass(frozen=True, slots=True)
class AttributeDemand:
    """Raw policy-weight sum for one attribute across weight-complete phase-roles."""

    attribute: str
    displayName: str
    abbreviation: str
    overall: int | None
    inPossession: int | None
    outOfPossession: int | None
    contributingPhaseRoles: int
    unavailableReason: str | None


@dataclass(frozen=True, slots=True)
class TacticObservation:
    """One count-based structural fact. Never advice or opposition judgement."""

    code: ObservationCode
    title: str
    explanation: str


@dataclass(frozen=True, slots=True)
class TacticAnalysis:
    """Immutable squad-independent demand report for one saved tactic."""

    tacticName: str
    scoringIdentity: str
    slotCount: int
    weightCompletePhaseRoles: int
    weightExpectedPhaseRoles: int
    demandCoverageReason: str | None
    slots: tuple[TacticSlotDemand, ...]
    overallDemand: tuple[AttributeDemand, ...]
    observations: tuple[TacticObservation, ...]


class TacticAnalysisService:
    """Build tactic demand from the object model and current role-assessment policy."""

    def __init__(
        self,
        vocabulary: TacticVocabulary,
        roleKnowledge: RoleKnowledgeService,
        attributes: tuple[AttributeDefinition, ...],
        scoringIdentity: str,
    ) -> None:
        self.vocabulary = vocabulary
        self.roleKnowledge = roleKnowledge
        self.attributes = attributes
        self.scoringIdentity = scoringIdentity

    def analysisBuild(self, tactic: object | None) -> TacticAnalysis | None:
        """Return demand for a saved tactic, or None when no object model exists.

        Do not consult an assigned footballer, CA/PA, or any squad model.
        """

        if tactic is None:
            return None

        linked = tuple(sorted(slotsLink(tactic), key=slotSortKey))
        slots = tuple(self._slotDemandBuild(item) for item in linked)
        expected = self._expectedPhaseRoles(tactic)
        completeRoles = tuple(
            role
            for slot in slots
            for role in (slot.ipRole, slot.oopRole)
            if role.resolutionState == "ready" and role.weights
        )
        demand = self._demandBuild(completeRoles)
        return TacticAnalysis(
            tacticName=str(getattr(tactic, "name", "") or ""),
            scoringIdentity=self.scoringIdentity,
            slotCount=len(slots),
            weightCompletePhaseRoles=len(completeRoles),
            weightExpectedPhaseRoles=expected,
            demandCoverageReason=self._coverageReason(slots, len(completeRoles), expected),
            slots=slots,
            overallDemand=demand,
            observations=self._observationsBuild(slots, demand),
        )

    ## slots

    def _slotDemandBuild(self, item: LinkedTacticSlot) -> TacticSlotDemand:
        ipRole = self._phaseRoleBuild("IP", item.ipPosition)
        oopRole = self._phaseRoleBuild("OOP", item.oopPosition)
        position = ipRole.canonicalPosition or oopRole.canonicalPosition
        return TacticSlotDemand(
            slotId=item.slotId,
            canonicalPosition=position,
            ipRole=ipRole,
            oopRole=oopRole,
            transition=self._transitionBuild(ipRole, oopRole, item.unavailableReason),
            linkageUnavailableReason=item.unavailableReason,
        )

    def _phaseRoleBuild(self, phase: PhaseName, position: object | None) -> TacticPhaseRole:
        """Resolve one phase-role. No Position is missingPhase, not unresolved."""

        if position is None:
            return TacticPhaseRole(
                phase=phase,
                roleCode=None,
                displayName="",
                abbreviation="",
                canonicalPosition="",
                resolutionState="missingPhase",
                weights=None,
                unavailableReason="Phase position is unavailable",
            )

        observed = self._observedRoleAbbreviation(position)
        roleCode = self._roleCodeResolve(position)
        canonicalPosition = self._positionCode(position)
        if roleCode is None:
            return TacticPhaseRole(
                phase=phase,
                roleCode=None,
                displayName=observed or "Unknown role",
                abbreviation=observed or "Unknown",
                canonicalPosition=canonicalPosition,
                resolutionState="unresolved",
                weights=None,
                unavailableReason=f"{phase} roleCode is unavailable",
            )

        displayName, abbreviation = self._roleLabels(roleCode, observed)
        rawWeights = self.roleKnowledge.weightsLoad(roleCode)
        if self._assessmentOptional(roleCode) and not rawWeights:
            return TacticPhaseRole(
                phase=phase,
                roleCode=roleCode,
                displayName=displayName,
                abbreviation=abbreviation,
                canonicalPosition=canonicalPosition,
                resolutionState="recognitionOnly",
                weights=None,
                unavailableReason=f"{phase} {displayName} is recognition only",
            )

        usable = self._usableWeights(rawWeights)
        if usable is None:
            return TacticPhaseRole(
                phase=phase,
                roleCode=roleCode,
                displayName=displayName,
                abbreviation=abbreviation,
                canonicalPosition=canonicalPosition,
                resolutionState="missingWeights",
                weights=None,
                unavailableReason=f"{phase} {displayName} has no usable assessment weights",
            )
        return TacticPhaseRole(
            phase=phase,
            roleCode=roleCode,
            displayName=displayName,
            abbreviation=abbreviation,
            canonicalPosition=canonicalPosition,
            resolutionState="ready",
            weights=usable,
            unavailableReason=None,
        )

    def _roleCodeResolve(self, position: object) -> str | None:
        """Use the Squad Assessment vocabulary path, not Role Depth's catalogue matcher."""

        canonical = str(getattr(position, "canonicalRole", "") or "").strip()
        if canonical:
            normalized = self.vocabulary.roleNormalize(canonical)
            if normalized.resolved:
                return str(normalized.value)
            exactPosition = self._positionCode(position)
            if canonical.casefold() != exactPosition.casefold():
                return canonical

        observed = self._observedRoleAbbreviation(position)
        if not observed:
            return None
        normalized = self.vocabulary.roleNormalize(observed)
        if normalized.resolved:
            return str(normalized.value)
        folded = observed.casefold()
        matches = [
            definition.roleCode
            for definition in self.roleKnowledge.definitionsList()
            if definition.displayName.casefold() == folded
            or any(abbreviation.casefold() == folded for abbreviation in definition.abbreviations)
        ]
        return matches[0] if len(matches) == 1 else None

    def _roleLabels(self, roleCode: str, observed: str) -> tuple[str, str]:
        role = self.vocabulary.roles.get(roleCode)
        definition = self._definitionFor(roleCode)
        displayName = str(
            (role.displayName if role is not None else "")
            or (definition.displayName if definition is not None else "")
            or roleCode
        )
        abbreviation = ""
        if role is not None and role.abbreviations:
            abbreviation = role.abbreviations[0]
        elif definition is not None and definition.abbreviations:
            abbreviation = definition.abbreviations[0]
        if not abbreviation:
            abbreviation = observed or roleCode
        return displayName, abbreviation

    def _definitionFor(self, roleCode: str) -> StoredRoleDefinition | None:
        return next(
            (
                definition
                for definition in self.roleKnowledge.definitionsList()
                if definition.roleCode == roleCode
            ),
            None,
        )

    def _assessmentOptional(self, roleCode: str) -> bool:
        role = self.vocabulary.roles.get(roleCode)
        return bool(role is not None and role.assessmentRequired is False)

    @staticmethod
    def _usableWeights(weights: Mapping[str, object] | None) -> dict[str, int] | None:
        """Return stripped 1-10 weights, or None when the mapping cannot be used.

        A non-integer or out-of-scale value fails the whole role, including
        Tracking identities that otherwise have packaged weights. Stored 0 is
        stripped as omission; an empty remainder is missing weights.
        """

        if not weights:
            return None
        usable: dict[str, int] = {}
        for attribute, weight in weights.items():
            if not isinstance(weight, int) or weight < _WEIGHT_MINIMUM or weight > _WEIGHT_MAXIMUM:
                return None
            if weight == 0:
                continue
            usable[str(attribute)] = weight
        return usable or None

    ## transitions

    @staticmethod
    def _transitionBuild(
        ipRole: TacticPhaseRole,
        oopRole: TacticPhaseRole,
        linkageUnavailableReason: str | None,
    ) -> PhaseTransition:
        """Classify only after linkage and both phase positions exist."""

        ipFamily = positionFamilyFor(ipRole.canonicalPosition) if ipRole.canonicalPosition else None
        oopFamily = (
            positionFamilyFor(oopRole.canonicalPosition) if oopRole.canonicalPosition else None
        )
        ipFamilyName = ipFamily.value if ipFamily is not None else None
        oopFamilyName = oopFamily.value if oopFamily is not None else None
        if linkageUnavailableReason:
            return PhaseTransition(
                "unavailable", ipFamilyName, oopFamilyName, linkageUnavailableReason
            )
        if ipRole.resolutionState == "missingPhase" or oopRole.resolutionState == "missingPhase":
            return PhaseTransition(
                "unavailable",
                ipFamilyName,
                oopFamilyName,
                "A phase position is unavailable",
            )
        if ipRole.roleCode is None or oopRole.roleCode is None:
            return PhaseTransition(
                "unavailable",
                ipFamilyName,
                oopFamilyName,
                "Role identity is unavailable",
            )
        if ipFamily is None or oopFamily is None:
            return PhaseTransition(
                "unavailable",
                ipFamilyName,
                oopFamilyName,
                "Position family is unavailable",
            )
        if ipRole.roleCode == oopRole.roleCode:
            return PhaseTransition("unchanged", ipFamilyName, oopFamilyName, "Unchanged")
        if ipFamily == oopFamily:
            return PhaseTransition(
                "roleChangeSameFamily",
                ipFamilyName,
                oopFamilyName,
                "Role change · same family",
            )
        return PhaseTransition(
            "familyChange",
            ipFamilyName,
            oopFamilyName,
            f"Family change · {ipFamilyName} → {oopFamilyName}",
        )

    ## demand

    def _demandBuild(
        self, completeRoles: tuple[TacticPhaseRole, ...]
    ) -> tuple[AttributeDemand, ...]:
        """Sum usable weights. A missing complete phase is Unavailable, not 0."""

        if not completeRoles:
            return ()
        completeIp = tuple(role for role in completeRoles if role.phase == "IP")
        completeOop = tuple(role for role in completeRoles if role.phase == "OOP")
        attributes = sorted(
            {attribute for role in completeRoles for attribute in (role.weights or ())}
        )
        attributeByName = {item.name: item for item in self.attributes}
        rows: list[AttributeDemand] = []
        for attribute in attributes:
            definition = attributeByName.get(attribute)
            overall = sum((role.weights or {}).get(attribute, 0) for role in completeRoles)
            ipTotal = (
                sum((role.weights or {}).get(attribute, 0) for role in completeIp)
                if completeIp
                else None
            )
            oopTotal = (
                sum((role.weights or {}).get(attribute, 0) for role in completeOop)
                if completeOop
                else None
            )
            contributing = sum(1 for role in completeRoles if attribute in (role.weights or {}))
            rows.append(
                AttributeDemand(
                    attribute=attribute,
                    displayName=(
                        definition.name.replace("_", " ").title()
                        if definition is not None
                        else attribute.replace("_", " ").title()
                    ),
                    abbreviation=definition.abbreviation if definition is not None else "",
                    overall=overall,
                    inPossession=ipTotal,
                    outOfPossession=oopTotal,
                    contributingPhaseRoles=contributing,
                    unavailableReason=None,
                )
            )
        return tuple(sorted(rows, key=lambda row: (-(row.overall or 0), row.attribute)))

    def _coverageReason(
        self,
        slots: tuple[TacticSlotDemand, ...],
        complete: int,
        expected: int,
    ) -> str | None:
        if expected == 0 or complete >= expected:
            return None
        reasons: list[str] = []
        excluded = tuple(
            f"{role.phase} {role.displayName or role.abbreviation or role.canonicalPosition}".strip()
            for slot in slots
            for role in (slot.ipRole, slot.oopRole)
            if role.resolutionState not in {"ready", "missingPhase"}
        )
        missing = sum(
            1
            for slot in slots
            for role in (slot.ipRole, slot.oopRole)
            if role.resolutionState == "missingPhase"
        )
        if excluded:
            reasons.append("Excluded: " + ", ".join(excluded))
        if missing:
            reasons.append(f"Unpaired or missing phase positions: {missing}")
        if not reasons:
            reasons.append(f"{complete} of {expected} phase-roles have usable assessment weights")
        return "; ".join(reasons)

    @staticmethod
    def _expectedPhaseRoles(tactic: object) -> int:
        """Count observed formation positions, not linked slots.

        Unlinked 11+11 therefore expects 22. An IP-only tactic expects 11.
        """

        total = 0
        for attribute in ("inPossession", "outOfPossession"):
            formation = getattr(tactic, attribute, None)
            total += len(tuple(getattr(formation, "positions", ()) or ()))
        return total

    ## observations

    def _observationsBuild(
        self,
        slots: tuple[TacticSlotDemand, ...],
        demand: tuple[AttributeDemand, ...],
    ) -> tuple[TacticObservation, ...]:
        observations: list[TacticObservation] = []
        observations.extend(self._repeatedRoles(slots))
        observations.extend(self._asymmetricFlanks(slots))
        observations.append(self._trackingCount(slots))
        familyChanges = self._familyChangeCount(slots)
        if familyChanges is not None:
            observations.append(familyChanges)
        concentration = self._demandConcentration(demand)
        if concentration is not None:
            observations.append(concentration)
        return tuple(observations)

    @staticmethod
    def _repeatedRoles(slots: tuple[TacticSlotDemand, ...]) -> tuple[TacticObservation, ...]:
        grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
        labels: dict[tuple[str, str], str] = {}
        for slot in slots:
            for role in (slot.ipRole, slot.oopRole):
                if role.roleCode is None:
                    continue
                key = (role.phase, role.roleCode)
                grouped[key].append(role.canonicalPosition or slot.canonicalPosition)
                labels[key] = role.displayName
        observations = []
        for (phase, roleCode), positions in sorted(grouped.items()):
            if len(positions) < 2:
                continue
            name = labels[(phase, roleCode)]
            observations.append(
                TacticObservation(
                    "repeatedRole",
                    f"{phase} {name}",
                    f"{name} is used in {len(positions)} {phase} slots: " + ", ".join(positions),
                )
            )
        return tuple(observations)

    @staticmethod
    def _asymmetricFlanks(slots: tuple[TacticSlotDemand, ...]) -> tuple[TacticObservation, ...]:
        """Compare L/R pairs inside one phase. IP/OOP pairing failure is not a flank gap."""

        byPhase: dict[str, dict[str, TacticPhaseRole]] = {"IP": {}, "OOP": {}}
        for slot in slots:
            for role in (slot.ipRole, slot.oopRole):
                if not role.canonicalPosition:
                    continue
                byPhase[role.phase][role.canonicalPosition] = role
        observations: list[TacticObservation] = []
        for phase, present in byPhase.items():
            for leftCode, rightCode in _FLANK_PAIRS:
                left = present.get(leftCode)
                right = present.get(rightCode)
                if left is None or right is None:
                    continue
                if left.roleCode is None or right.roleCode is None:
                    observations.append(
                        TacticObservation(
                            "asymmetricFlank",
                            f"{phase} {leftCode}/{rightCode}",
                            f"{phase} {leftCode}/{rightCode} role identity is unresolved",
                        )
                    )
                    continue
                if left.roleCode == right.roleCode:
                    continue
                observations.append(
                    TacticObservation(
                        "asymmetricFlank",
                        f"{phase} {leftCode}/{rightCode}",
                        f"{phase} {leftCode} {left.displayName} vs {rightCode} {right.displayName}",
                    )
                )
        return tuple(observations)

    @staticmethod
    def _trackingCount(slots: tuple[TacticSlotDemand, ...]) -> TacticObservation:
        codes = tuple(
            role.roleCode
            for slot in slots
            for role in (slot.ipRole, slot.oopRole)
            if role.roleCode in TRACKING_ROLE_CODES
        )
        if not codes:
            explanation = "0 tracking phase-roles"
        else:
            explanation = f"{len(codes)} tracking phase-roles ({', '.join(codes)})"
        return TacticObservation("trackingRoleCount", "Tracking roles", explanation)

    @staticmethod
    def _familyChangeCount(slots: tuple[TacticSlotDemand, ...]) -> TacticObservation | None:
        classifiable = tuple(
            slot for slot in slots if slot.transition.classification != "unavailable"
        )
        if not classifiable:
            return None
        changed = sum(
            1 for slot in classifiable if slot.transition.classification == "familyChange"
        )
        return TacticObservation(
            "familyChangeCount",
            "Family changes",
            f"{changed} of {len(classifiable)} slots classifiable",
        )

    @staticmethod
    def _demandConcentration(demand: tuple[AttributeDemand, ...]) -> TacticObservation | None:
        if not demand:
            return None
        top = demand[:3]
        explanation = ", ".join(
            f"{row.displayName} {row.overall}" for row in top if row.overall is not None
        )
        return TacticObservation("demandConcentration", "Demand concentration", explanation)

    ## evidence helpers

    @staticmethod
    def _observedRoleAbbreviation(position: object) -> str:
        profile = getattr(position, "roleProfile", None)
        name = str(getattr(profile, "name", "") or "").strip()
        if name.casefold() not in {"", "observed role", "unresolved"}:
            return name
        description = str(getattr(profile, "description", "") or "").strip()
        if description:
            observed = description.split(" (", 1)[0].strip()
            if observed.casefold() not in {"", "observed role", "unresolved"}:
                return observed
        return ""

    @staticmethod
    def _positionCode(position: object) -> str:
        canonical = getattr(position, "canonicalPosition", None)
        if canonical:
            return str(canonical)
        identity = getattr(position, "identity", None)
        value = getattr(identity, "value", None)
        return str(value or "")
