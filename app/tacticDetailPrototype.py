"""Prototype data for the requirement 009 tactic detail workspace."""

from __future__ import annotations

from fmsat.app.tacticDetailModel import DisplaySlot, TacticDetailModel


def tacticDetailPrototype() -> TacticDetailModel:
    """Return the fictional model used by the tactic detail prototype."""

    formationSlots = (
        DisplaySlot("01", "STC", "CHF", "Attack", 0.50, 0.12, "striker"),
        DisplaySlot("02", "AML", "IF", "Attack", 0.22, 0.28, "attackingMidfield"),
        DisplaySlot("03", "AMC", "AM", "Support", 0.50, 0.31, "attackingMidfield"),
        DisplaySlot("04", "AMR", "W", "Attack", 0.78, 0.28, "attackingMidfield"),
        DisplaySlot("05", "WBL", "AWB", "Support", 0.12, 0.51, "defensiveMidfield"),
        DisplaySlot("06", "DM", "DLP", "Defend", 0.50, 0.54, "defensiveMidfield"),
        DisplaySlot("07", "WBR", "AWB", "Support", 0.88, 0.51, "defensiveMidfield"),
        DisplaySlot("08", "DCL", "BCB", "Defend", 0.25, 0.73, "defence"),
        DisplaySlot("09", "DC", "CB", "Defend", 0.50, 0.77, "defence"),
        DisplaySlot("10", "DCR", "BCB", "Defend", 0.75, 0.73, "defence"),
        DisplaySlot("11", "GK", "BGK", "Support", 0.50, 0.91, "goalkeeper"),
    )
    moved = {
        "02": (0.18, 0.39),
        "04": (0.82, 0.39),
        "05": (0.13, 0.62),
        "07": (0.87, 0.62),
    }
    outOfPossessionSlots = tuple(
        DisplaySlot(
            slot.slotId,
            slot.position,
            slot.role,
            slot.duty,
            *moved.get(slot.slotId, (slot.x, slot.y)),
            slot.row,
            slot.player,
        )
        for slot in formationSlots
    )
    return TacticDetailModel(
        formation="3–3–3–1",
        mentality="Positive",
        status="Ready",
        assignedSquads="First Team · U21s",
        updated="08 Aug 2026",
        revisions=("Current · v3", "v2 · 18 Jun 2026", "v1 · 02 Jun 2026"),
        formationSlots=formationSlots,
        outOfPossessionSlots=outOfPossessionSlots,
        summaryItems=(
            ("Positive mentality", "Explicitly stored"),
            ("Higher tempo", "In possession"),
            ("Counter press", "Transition · enabled"),
            ("Higher defensive line", "Out of possession"),
        ),
        notes="Aggressive central overload with width arriving from the wing-backs.",
        instructionGroups=(
            (
                "Build Up",
                (
                    ("Passing directness", "Slightly shorter"),
                    ("Tempo", "Higher"),
                    ("Patience", "Work ball into box"),
                    ("Goalkeeper distribution", "Centre-backs"),
                ),
            ),
            (
                "Attack",
                (
                    ("Attacking width", "Fairly narrow"),
                    ("Creative freedom", "Be more expressive"),
                    ("Dribbling", "Run at defence"),
                    ("Supporting runs", "Overlap left"),
                ),
            ),
            (
                "Transition",
                (
                    ("Counter", "On"),
                    ("Counter press", "On"),
                    ("Distribution speed", "Distribute quickly"),
                ),
            ),
            (
                "Defence",
                (
                    ("Line of engagement", "High press"),
                    ("Defensive line", "Higher"),
                    ("Trigger press", "Much more often"),
                    ("Pressing trap", "Outside"),
                ),
            ),
        ),
    )
