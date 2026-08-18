"""UI-ready models for the squad assessment workspace."""

from __future__ import annotations

import re
from dataclasses import dataclass

from fmsat.app.presentation import (
    playerNameDisplay,
    positionSortKey,
    roleAbbreviationDisplay,
    rolePositionSortKey,
)
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
class RequiredSlotDisplay:
    """One simultaneous tactic slot rendered from FMSAT role-depth intelligence."""

    position: str
    ipRole: str
    oopRole: str
    primary: str
    backup: str
    primaryEvidence: str
    backupEvidence: str


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
    requiredSlots: tuple[RequiredSlotDisplay, ...] = ()


def squadDetailModelBuild(assessment: SquadAssessment) -> SquadDetailModel:
    """Map one domain assessment into deterministic squad-viewer text."""

    visibleRoles = tuple(
        sorted(
            (
                role
                for role in assessment.roles
                if not role.roleCode.startswith("capturedRole")
            ),
            key=rolePositionSortKey,
        )
    )
    catalogueSource = assessment.allRoles or assessment.roles
    visibleCatalogue = tuple(
        role
        for role in catalogueSource
        if not role.roleCode.startswith("capturedRole")
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
            if current is None or proposed[0] > current[0] or (
                proposed[0] == current[0]
                and proposed[1].casefold() < current[1].casefold()
            ):
                bestRoles[key] = proposed

    displayNames = {
        player.name: playerNameDisplay(player.name)
        for player in assessment.squad.players
    }

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
                    name=playerNameDisplay(candidate.player.name),
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
            coverage = (
                f"Best: {playerNameDisplay(role.bestCandidate or '')} · "
                "no calculated backup"
            )
        else:
            coverage = (
                f"Best: {playerNameDisplay(role.bestCandidate or '')} · "
                f"Backup: {playerNameDisplay(role.backupCandidate)}"
            )
        roles.append(
            RoleDisplay(
                roleCode=role.roleCode,
                displayName=role.displayName,
                abbreviation=roleAbbreviationDisplay(role.roleCode, role.abbreviation),
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
                name=playerNameDisplay(player.player.name),
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
                alternatives=", ".join(role[2] for role in alternatives)
                or "Unavailable",
            )
        )

    requiredSlots = tuple(
        _requiredSlotDisplay(slot)
        for slot in sorted(
            assessment.requiredSlots,
            key=lambda slot: (*positionSortKey(slot.position), slot.slotId.casefold()),
        )
    )

    findings = tuple(
        AnalysisFindingDisplay(
            category,
            _playerNamesReplace(finding.title, displayNames),
            _playerNamesReplace(finding.explanation, displayNames),
        )
        for category, group in (
            ("Weak position", assessment.weakRoles),
            ("Role duplication", assessment.duplicatedRoles),
            ("Unused strength", assessment.unusedStrengths),
        )
        for finding in group
        if not finding.code.startswith("capturedRole")
        and not (
            category == "Weak position"
            and finding.explanation.startswith("No player has complete evidence")
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
        requiredPositionCount=assessment.requiredPositionCount,
        roles=tuple(roles),
        scoringIdentity=assessment.scoringIdentity,
        playerRoles=tuple(playerRoles),
        findings=findings,
        requiredSlots=requiredSlots,
    )


def _requiredSlotDisplay(slot) -> RequiredSlotDisplay:
    """Render one slot with phase roles and candidates who satisfy both phases."""

    phaseRoles = {
        role.phase: roleAbbreviationDisplay(role.roleCode or "", role.abbreviation)
        for role in slot.roles
    }
    primary, primaryEvidence = _slotCandidateDisplay(slot, slot.bestCandidate)
    backup, backupEvidence = _slotCandidateDisplay(slot, slot.backupCandidate)
    if slot.unavailableReason is not None:
        primary = "Unavailable"
        primaryEvidence = slot.unavailableReason
        backup = "Unavailable"
        backupEvidence = slot.unavailableReason
    elif slot.uncovered and slot.bestCandidate is None:
        primary = "Uncovered"
        primaryEvidence = "No player has complete calculable evidence for every phase role."
        backup = "—"
        backupEvidence = primaryEvidence
    elif slot.backupCandidate is None:
        backup = "—"
        backupEvidence = "No independent backup remains after the primary assignment."
    return RequiredSlotDisplay(
        position=slot.position,
        ipRole=phaseRoles.get("IP", "—"),
        oopRole=phaseRoles.get("OOP", "—"),
        primary=primary,
        backup=backup,
        primaryEvidence=primaryEvidence,
        backupEvidence=backupEvidence,
    )


def _slotCandidateDisplay(slot, playerName: str | None) -> tuple[str, str]:
    """Show one assigned player with IP/OOP fit evidence proving complete slot coverage."""

    if playerName is None:
        return "—", "Unavailable"
    candidate = next(
        (
            item
            for item in slot.candidates
            if item.player.name.casefold() == playerName.casefold()
        ),
        None,
    )
    if candidate is None or candidate.score is None:
        return playerNameDisplay(playerName), "Required slot evidence is unavailable"

    phaseScores = []
    evidence = []
    for roleFit in candidate.roleFits:
        score = roleFit.genericRoleFit.score
        scoreText = f"{score:.1f}" if score is not None else "Unavailable"
        phaseScores.append(scoreText)
        evidence.append(f"{roleFit.phase} {roleFit.displayName}: {scoreText}")
    scoreText = " / ".join(phaseScores)
    display = playerNameDisplay(playerName)
    if scoreText:
        display = f"{display} · {scoreText}"
    evidence.append(f"Combined slot score: {candidate.score:.1f}")
    return display, "; ".join(evidence)


def _playerNamesReplace(text: str, displayNames: dict[str, str]) -> str:
    """Render embedded player identities and delimit surname-first lists unambiguously."""

    rendered = text
    for storedName, displayName in sorted(
        displayNames.items(), key=lambda item: len(item[0]), reverse=True
    ):
        rendered = rendered.replace(storedName, displayName)
    return re.sub(
        r"(?<=[A-Za-zÀ-ÖØ-öø-ÿ.'-]), (?=[A-ZÀ-ÖØ-Þ][^,.;:]+,)",
        "; ",
        rendered,
    )
