"""Map football object-model tactics into tactic-detail UI models."""

from __future__ import annotations

import re
from datetime import datetime

from fmsat.app.tacticDetailModel import DisplaySlot, TacticDetailModel
from fmsat.core.parser import TacticVocabulary
from fmsat.tactics.formation import Formation
from fmsat.tactics.position import Position
from fmsat.tactics.positionIdentity import PositionIdentity
from fmsat.tactics.tactic import Tactic

_TACTIC_VOCABULARY = TacticVocabulary()


def tacticDetailModelBuild(
    tactic: Tactic,
    *,
    source: str,
    complete: bool,
    confirmed: bool,
    metadata: dict[str, str] | None = None,
    phaseSlots: (
        dict[str, tuple[tuple[str, str, str, str, float, float, str | None], ...]] | None
    ) = None,
    assignedSquads: tuple[str, ...] = (),
    updatedAt: datetime | None = None,
) -> TacticDetailModel:
    """Build one UI detail model from one tactic object-model tactic."""

    safeMetadata = metadata or {}
    formationSlots = _phaseSlotsResolve(
        phaseSlots,
        "inPossession",
        fallback=tactic.inPossession,
    )
    outOfPossessionSlots = _phaseSlotsResolve(
        phaseSlots,
        "outOfPossession",
        fallback=tactic.outOfPossession,
    )
    inPossessionName = _shapeNameResolve(safeMetadata, "inPossession", tactic.inPossession.name)
    outOfPossessionName = _shapeNameResolve(
        safeMetadata,
        "outOfPossession",
        tactic.outOfPossession.name,
    )
    formationLabel = _formationLabelResolve(tactic.name, safeMetadata, inPossessionName)
    mentalityLabel = _mentalityResolve(safeMetadata)
    summaryItems = (
        ("Model Source", "Saved tactic model" if source == "objectModel" else "Structured OCR"),
        ("In-Possession Shape", inPossessionName),
        ("Out-of-Possession Shape", outOfPossessionName),
        (
            "Instruction Coverage",
            f"{len(tactic.inPossession.instructions)} in-possession, "
            f"{len(tactic.outOfPossession.instructions)} out-of-possession, "
            f"{len(tactic.transition.instructions)} transition",
        ),
    )
    return TacticDetailModel(
        formation=formationLabel,
        mentality=mentalityLabel,
        status=_statusText(source, complete, confirmed),
        assignedSquads=" · ".join(assignedSquads) if assignedSquads else "None",
        updated=updatedAt.strftime("%d %b %Y") if updatedAt is not None else "Unknown",
        revisions=("Current",),
        formationSlots=formationSlots,
        outOfPossessionSlots=outOfPossessionSlots,
        summaryItems=summaryItems,
        notes=_notesText(source),
        instructionGroups=(
            ("In Possession", _instructionsView(tactic.inPossession)),
            ("Out Of Possession", _instructionsView(tactic.outOfPossession)),
            ("Transition", _instructionsTransitionView(tactic)),
        ),
    )


def tacticDetailIncompleteModelBuild(
    tacticName: str,
    *,
    reason: str,
    assignedSquads: tuple[str, ...] = (),
    updatedAt: datetime | None = None,
) -> TacticDetailModel:
    """Build a safe incomplete-data model for tactics without structured data."""

    return TacticDetailModel(
        formation="Unknown",
        mentality="Not available",
        status="Incomplete data",
        assignedSquads=" · ".join(assignedSquads) if assignedSquads else "None",
        updated=updatedAt.strftime("%d %b %Y") if updatedAt is not None else "Unknown",
        revisions=("Current",),
        formationSlots=(),
        outOfPossessionSlots=(),
        summaryItems=(
            ("Tactic", tacticName),
            ("Availability", "Structured tactic data is missing"),
            (
                "How to complete",
                "Use Process to build the model from existing captures when available",
            ),
            ("Load reason", reason),
        ),
        notes=(
            "This tactic remains accessible, but no structured or saved object-model "
            "representation is available yet."
        ),
        instructionGroups=(
            ("In Possession", ()),
            ("Out Of Possession", ()),
            ("Transition", ()),
        ),
    )


def _instructionsTransitionView(tactic: Tactic) -> tuple[tuple[str, str], ...]:
    """Return rendered transition instruction rows for the detail UI."""

    return tuple(
        (instruction.name, value.name)
        for instruction, value in sorted(
            tactic.transition.instructions.items(),
            key=lambda item: item[0].name.casefold(),
        )
    )


def _instructionsView(formation: Formation) -> tuple[tuple[str, str], ...]:
    """Return rendered formation instruction rows for the detail UI."""

    return tuple(
        (instruction.name, value.name)
        for instruction, value in sorted(
            formation.instructions.items(),
            key=lambda item: item[0].name.casefold(),
        )
    )


def _notesText(source: str) -> str:
    """Return detail notes describing where the tactic model originated."""

    if source == "objectModel":
        return "Loaded from the persisted object-model tactic tables."
    return "Built from structured OCR extraction and shown as the current tactic model."


def _camelWords(text: str) -> str:
    """Convert camelCase and underscore identifiers into readable words."""

    words = re.sub(r"(?<!^)(?=[A-Z])", " ", text).replace("_", " ")
    return " ".join(words.split())


def _formationLabelResolve(tacticName: str, metadata: dict[str, str], fallback: str) -> str:
    """Resolve the best user-facing formation value from metadata and fallbacks."""

    for key in ("formationName", "formation"):
        value = metadata.get(key, "").strip()
        if value:
            return value

    if fallback.strip() and fallback not in {"inPossession", "outOfPossession"}:
        return fallback.strip()

    # When no explicit formation value is stored, extract common leading
    # shape notation from the tactic name (for example "3-4-2-1 High Press").
    match = re.match(r"\s*(\d(?:-\d){2,5})\b", tacticName)
    if match is not None:
        return match.group(1)
    return "Unknown"


def _mentalityResolve(metadata: dict[str, str]) -> str:
    """Resolve mentality from explicit structured metadata when present."""

    value = metadata.get("mentality", "").strip()
    if not value:
        return "Not captured"
    return _camelWords(value).title()


def _phaseSlotsResolve(
    phaseSlots: dict[str, tuple[tuple[str, str, str, str, float, float, str | None], ...]] | None,
    phase: str,
    *,
    fallback: Formation,
) -> tuple[DisplaySlot, ...]:
    """Use persisted structured phase slots when available, else derive fallbacks."""

    if phaseSlots is None:
        return _slotsBuild(fallback)
    values = phaseSlots.get(phase, ())
    if not values:
        return _slotsBuild(fallback)

    slots: list[DisplaySlot] = []
    for slotId, position, role, duty, x, y, player in values:
        roleLabel = _roleAbbreviation(role)
        slots.append(
            DisplaySlot(
                slotId=slotId,
                position=position,
                role=roleLabel,
                duty=duty,
                x=max(0.0, min(1.0, float(x))),
                y=max(0.0, min(1.0, float(y))),
                row=_rowFromPosition(position),
                player=player,
            )
        )
    return tuple(slots)


def _shapeNameResolve(metadata: dict[str, str], key: str, fallback: str) -> str:
    """Resolve one phase shape name from metadata with safe placeholders."""

    metadataKey = "inPossessionName" if key == "inPossession" else "outOfPossessionName"
    value = metadata.get(metadataKey, "").strip()
    if value and value not in {"inPossession", "outOfPossession"}:
        return value
    if fallback.strip() and fallback not in {"inPossession", "outOfPossession"}:
        return fallback.strip()
    return "Not captured"


def _roleAbbreviation(role: str) -> str:
    """Return short role code for pitch labels from configured role vocabulary."""

    normalized = _TACTIC_VOCABULARY.roleNormalize(role)
    if normalized.resolved:
        definition = _TACTIC_VOCABULARY.roles.get(normalized.value)
        if definition is not None and definition.abbreviations:
            return definition.abbreviations[0]

    # For unresolved custom roles, keep labels compact with an acronym fallback.
    words = _camelWords(role)
    if not words:
        return role
    initials = "".join(word[0] for word in words.split() if word)
    if len(initials) >= 2:
        return initials.upper()
    return role


def _rowFromPosition(position: str) -> str:
    """Map canonical position code to one broad pitch row label."""

    if position == "GK":
        return "goalkeeper"
    if position.startswith("D") or position.startswith("WB"):
        return "defence"
    if position.startswith("DM"):
        return "defensiveMidfield"
    if position.startswith("M"):
        return "midfield"
    if position.startswith("AM"):
        return "attackingMidfield"
    return "striker"


def _positionBase(position: Position) -> tuple[float, float, str]:
    """Return baseline coordinates and row label for one position identity."""

    if position.identity is PositionIdentity.GK:
        return 0.50, 0.91, "goalkeeper"
    if position.identity in {PositionIdentity.DL, PositionIdentity.WBL}:
        return 0.20, 0.74, "defence"
    if position.identity in {PositionIdentity.DR, PositionIdentity.WBR}:
        return 0.80, 0.74, "defence"
    if position.identity is PositionIdentity.DC:
        return 0.50, 0.76, "defence"
    if position.identity is PositionIdentity.DM:
        return 0.50, 0.60, "defensiveMidfield"
    if position.identity is PositionIdentity.ML:
        return 0.24, 0.47, "midfield"
    if position.identity is PositionIdentity.MR:
        return 0.76, 0.47, "midfield"
    if position.identity is PositionIdentity.MC:
        return 0.50, 0.49, "midfield"
    if position.identity is PositionIdentity.AML:
        return 0.22, 0.30, "attackingMidfield"
    if position.identity is PositionIdentity.AMR:
        return 0.78, 0.30, "attackingMidfield"
    if position.identity is PositionIdentity.AMC:
        return 0.50, 0.31, "attackingMidfield"
    return 0.50, 0.12, "striker"


def _slotsBuild(formation: Formation) -> tuple[DisplaySlot, ...]:
    """Build display slots, preferring evidence retained by the object model."""

    grouped: dict[PositionIdentity, list[Position]] = {}
    for position in formation.positions:
        grouped.setdefault(position.identity, []).append(position)

    slots: list[DisplaySlot] = []
    slotIndex = 1
    for identity in PositionIdentity:
        siblings = grouped.get(identity, [])
        if not siblings:
            continue
        baseX, baseY, row = _positionBase(siblings[0])
        offsetStart = -(len(siblings) - 1) / 2
        for siblingIndex, position in enumerate(siblings):
            fallbackX = baseX + (offsetStart + siblingIndex) * 0.12
            x = position.x if position.x is not None else fallbackX
            y = position.y if position.y is not None else baseY
            slots.append(
                DisplaySlot(
                    slotId=position.slotId or f"{slotIndex:02d}",
                    position=position.identity.value,
                    role=position.role.identity.value,
                    duty=position.duty or "Unresolved",
                    x=max(0.0, min(1.0, x)),
                    y=max(0.0, min(1.0, y)),
                    row=row,
                    player=position.player,
                )
            )
            slotIndex += 1
    return tuple(slots)


def _statusText(source: str, complete: bool, confirmed: bool) -> str:
    """Return one concise status line for the detail header cards."""

    if source == "objectModel":
        return "Saved model"
    qualifiers = []
    qualifiers.append("confirmed" if confirmed else "unconfirmed")
    qualifiers.append("complete" if complete else "partial")
    return "Structured " + ", ".join(qualifiers)
