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

    visibleRoles = tuple(
        sorted(
            (role for role in assessment.roles if not role.roleCode.startswith("capturedRole")),
            key=_rolePositionSortKey,
        )
    )
    catalogueSource = assessment.allRoles or assessment.roles
    visibleCatalogue = tuple(
        role for role in catalogueSource if not role.roleCode.startswith("capturedRole")
    )

    bestRoles: dict[str, tuple[float, str]] = {}
    for role in visibleCatalogue:
        for candidate in role.candidates:
            score = candidate.genericRoleFit.score
            if score is None:
                continue
            key = candidate.player.name.casefold()
            current = bestRoles.get(key)
            proposed = (score, role.displayName)
            if (
                current is None
                or proposed[0] > current[0]
                or (proposed[0] == current[0] and proposed[1].casefold() < current[1].casefold())
            ):
                bestRoles[key] = proposed

    roles = []
    for role in visibleRoles:
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
        for role in visibleCatalogue
        for candidate in role.candidates
    }
    catalogueByPlayer: dict[str, list[tuple[float, str, str]]] = {}
    for role in visibleCatalogue:
        for candidate in role.candidates:
            score = candidate.genericRoleFit.score
            if score is None:
                continue
            catalogueByPlayer.setdefault(candidate.player.name.casefold(), []).append(
                (score, role.roleCode, role.displayName)
            )

    playerRoles = []
    for player in assessment.players:
        ordered = sorted(
            catalogueByPlayer.get(player.player.name.casefold(), ()),
            key=lambda item: (-item[0], item[2].casefold()),
        )
        best = ordered[0] if ordered else None
        alternatives = ordered[1:4]
        bestFit = (
            catalogueFits.get((best[1], player.player.name.casefold()))
            if best is not None
            else None
        )
        playerRoles.append(
            PlayerRoleDisplay(
                name=player.player.name,
                bestRole=best[2] if best is not None else "Unavailable",
                bestScore=f"{best[0]:.1f}" if best is not None else "Unavailable",
                bestBreakdown=(
                    "; ".join(
                        f"{item.attribute}: {item.value} × {item.weight} = "
                        f"{item.weightedPoints}/{item.maximumPoints}"
                        for item in bestFit.contributions
                    )
                    if bestFit is not None
                    else player.unavailableReason or "Required data is unavailable"
                ),
                alternatives=", ".join(role[2] for role in alternatives) or "Unavailable",
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
        if not finding.code.startswith("capturedRole")
    )
    return SquadDetailModel(
        squad=assessment.squad,
        tacticName=assessment.tacticName or "No tactic selected",
        availableTactics=assessment.availableTactics,
        sourceStatus=(
            "Regeneration required — newer squad screenshots exist"
            if assessment.squad.regenerationRequired
            else (
                "Edited model — screenshots superseded"
                if assessment.squad.evidenceSuperseded
                else "Generated from screenshot evidence"
            )
        ),
        updated=assessment.squad.updatedAt.strftime("%d %b %Y %H:%M"),
        requiredPositionCount=assessment.requiredPositionCount,
        roles=tuple(roles),
        scoringIdentity=assessment.scoringIdentity,
        playerRoles=tuple(playerRoles),
        findings=findings,
    )


def _rolePositionSortKey(role) -> tuple[int, int, str, str]:
    """Order roles using FM pitch order: GK, defence, DM, M, AM, ST."""

    positionKeys = [_positionSortKey(position) for position in role.positions]
    line, side = min(positionKeys, default=(6, 3))
    return line, side, role.displayName.casefold(), role.roleCode.casefold()


def _positionSortKey(position: str) -> tuple[int, int]:
    compact = position.upper().replace(" ", "").replace("(", "").replace(")", "")
    if compact == "GK":
        line = 0
    elif compact.startswith("WB") or (compact.startswith("D") and not compact.startswith("DM")):
        line = 1
    elif compact.startswith("DM"):
        line = 2
    elif compact.startswith("M") and not compact.startswith("AM"):
        line = 3
    elif compact.startswith("AM"):
        line = 4
    elif compact.startswith("ST"):
        line = 5
    else:
        line = 6
    side = (
        0
        if compact.endswith("L")
        else 1 if compact.endswith("C") else 2 if compact.endswith("R") else 3
    )
    return line, side
