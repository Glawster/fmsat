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
class SquadDetailModel:
    """All display data and editable squad facts required by the squad viewer."""

    squad: SquadModel
    tacticName: str
    availableTactics: tuple[str, ...]
    sourceStatus: str
    updated: str
    roles: tuple[RoleDisplay, ...]


def squadDetailModelBuild(assessment: SquadAssessment) -> SquadDetailModel:
    """Map one domain assessment into deterministic squad-viewer text."""

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
        roles=tuple(roles),
    )
