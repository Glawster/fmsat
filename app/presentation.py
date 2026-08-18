"""Shared presentation-only formatting used by FMSAT application views."""

from __future__ import annotations


def playerNameDisplay(name: str) -> str:
    """Render a stored player name as ``Surname, Given names`` without changing identity."""

    value = name.strip()
    if not value or "," in value:
        return value
    parts = value.split()
    if len(parts) < 2:
        return value
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def playerNameStorage(name: str) -> str:
    """Convert the editable surname-first presentation back to stored name order."""

    value = name.strip()
    if "," not in value:
        return value
    surname, givenNames = value.split(",", 1)
    givenNames = givenNames.strip()
    surname = surname.strip()
    return f"{givenNames} {surname}".strip()


def playerNameSortKey(name: str) -> tuple[str, str]:
    """Return a stable surname-first sort key for either stored or display form."""

    display = playerNameDisplay(name)
    if "," not in display:
        return display.casefold(), ""
    surname, givenNames = display.split(",", 1)
    return surname.strip().casefold(), givenNames.strip().casefold()
