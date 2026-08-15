"""UI-ready models for the squad assessment workspace."""

from __future__ import annotations

from dataclasses import dataclass

from fmsat.core.squadAssessment import SquadAssessment
from fmsat.core.squadModel import SquadModel


@dataclass(frozen=True, slots=True)
class CandidateDisplay:
    """One player candidate and its transparent role-fit presentation."""

    name: str
    positions: str
    score: str
    bestRole: str
    breakdown: str
    available: bool


@dataclass(frozen=True, slots=True)
class RoleDisplay:
    """One unique canonical role displayed in the Roles tab."""

    roleCode: str
    displayName: str
    abbreviation: str
    positions: str
    phases: str
    coverage: str
    candidates: tuple[CandidateDisplay, ...]


@dataclass(frozen=True, slots=True)
class PlayerRoleDisplay:
    """One player's ordered Generic Role Fit summary."""

    name: str
    bestRole: str
    bestScore: str
    bestBreakdown: str
    alternatives: str


@dataclass(frozen=True, slots=True)
class AnalysisFindingDisplay:
    """One squad-level finding and its evidence statement."""

    category: str
    subject: str
    explanation: str


@dataclass(frozen=True, slots=True)
class SquadDetailModel:
    """All display data and editable squad facts required by the squad viewer."""

    squad: SquadModel
    tacticName: str
    availableTactics: tuple[str, ...]
    sourceStatus: str
    updated: str
    requiredPositionCount: int
    roles: tuple[RoleDisplay, ...]
    scoringIdentity: str = "Unavailable"
    playerRoles: tuple[PlayerRoleDisplay, ...] = ()
    findings: tuple[AnalysisFindingDisplay, ...] = ()


def squadDetailModelBuild(assessment: SquadAssessment) -> SquadDetailModel:
    """Map one domain assessment into deterministic squad-viewer text."""

    bestRoles: dict[str, tuple[float, str]] = {}
    for role in assessment.roles:
        for candidate in role.candidates:
            score = candidate.genericRoleFit.score
            if score is None:
                continue
            key = candidate.player.name.casefold()
            current = bestRoles.get(key)
            proposed = (score, role.displayName)
            if current is None or proposed[0] > current[0] or (
                proposed[0] == current[0] and proposed[1].casefold() < current[1].casefold()
            ):
                bestRoles[key] = proposed

    roles = []
    for role in assessment.roles:
        candidates = []
        for candidate in role.candidates:
            fit = candidate.genericRoleFit
            if fit.available:
                breakdown = "; ".join(
                    f"{item.attribute}: {item.value} × {item.weight} = "
                    f"{item.weightedPoints}/{item.maximumPoints}"
                    for item in fit.contributions
                )
                score = f"{fit.score:.1f}"
            else:
                breakdown = fit.unavailableReason or "Required data is unavailable"
                score = "Unavailable"
            candidates.append(
                CandidateDisplay(
                    name=candidate.player.name,
                    positions=candidate.player.positions,
                    score=score,
                    bestRole=bestRoles.get(
                        candidate.player.name.casefold(),
                        (0.0, "Unavailable"),
                    )[1],
                    breakdown=breakdown,
                    available=fit.available,
                )
            )
        if role.uncovered:
            coverage = "Uncovered — no player has a calculable role fit"
        elif role.backupCandidate is None:
            coverage = f"Best: {role.bestCandidate} · no calculated backup"
        else:
            coverage = f"Best: {role.bestCandidate} · Backup: {role.backupCandidate}"
        roles.append(
            RoleDisplay(
                roleCode=role.roleCode,
                displayName=role.displayName,
                abbreviation=role.abbreviation,
                positions=", ".join(role.positions),
                phases=", ".join(role.phases),
                coverage=coverage,
                candidates=tuple(candidates),
            )
        )
    catalogueFits = {
        (role.roleCode, candidate.player.name.casefold()): candidate.genericRoleFit
        for role in assessment.allRoles
        for candidate in role.candidates
    }
    playerRoles = []
    for player in assessment.players:
        bestFit = (
            catalogueFits.get((player.bestRole.roleCode, player.player.name.casefold()))
            if player.bestRole is not None
            else None
        )
        playerRoles.append(
            PlayerRoleDisplay(
                name=player.player.name,
                bestRole=(
                    player.bestRole.displayName
                    if player.bestRole is not None
                    else "Unavailable"
                ),
                bestScore=(
                    f"{player.bestRole.score:.1f}"
                    if player.bestRole is not None
                    else "Unavailable"
                ),
                bestBreakdown=(
                    "; ".join(
                        f"{item.attribute}: {item.value} × {item.weight} = "
                        f"{item.weightedPoints}/{item.maximumPoints}"
                        for item in bestFit.contributions
                    )
                    if bestFit is not None
                    else player.unavailableReason or "Required data is unavailable"
                ),
                alternatives=(
                    ", ".join(role.displayName for role in player.alternativeRoles)
                    or "Unavailable"
                ),
            )
        )
    findings = tuple(
        AnalysisFindingDisplay(category, finding.title, finding.explanation)
        for category, group in (
            ("Weak position", assessment.weakRoles),
            ("Role duplication", assessment.duplicatedRoles),
            ("Unused strength", assessment.unusedStrengths),
        )
        for finding in group
    )
    return SquadDetailModel(
        squad=assessment.squad,
        tacticName=assessment.tacticName or "No tactic selected",
        availableTactics=assessment.availableTactics,
        sourceStatus=(
            "Regeneration required — newer squad screenshots exist"
            if assessment.squad.regenerationRequired
            else "Edited model — screenshots superseded"
            if assessment.squad.evidenceSuperseded
            else "Generated from screenshot evidence"
        ),
        updated=assessment.squad.updatedAt.strftime("%d %b %Y %H:%M"),
        requiredPositionCount=assessment.requiredPositionCount,
        roles=tuple(roles),
        scoringIdentity=assessment.scoringIdentity,
        playerRoles=tuple(playerRoles),
        findings=findings,
    )
