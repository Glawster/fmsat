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


def playerSurnameDisplay(name: str) -> str:
    """Return only the surname for deliberately compact coverage summaries."""

    display = playerNameDisplay(name)
    if "," in display:
        return display.split(",", 1)[0].strip()
    return display


def roleAbbreviationDisplay(roleCode: str, abbreviation: str) -> str:
    """Use a confirmed abbreviation, otherwise expose the missing role knowledge."""

    code = roleCode.strip()
    candidate = abbreviation.strip()
    if candidate and candidate.casefold() != code.casefold():
        return candidate
    return "Unknown"


def positionSortKey(position: str) -> tuple[int, int]:
    """Order FM positions from forwards back to goalkeeper, then left-centre-right."""

    compact = (
        position.upper()
        .replace(" ", "")
        .replace("(", "")
        .replace(")", "")
    )
    if compact.startswith("ST"):
        line = 0
    elif compact.startswith("AM"):
        line = 1
    elif compact.startswith("M") and not compact.startswith("AM"):
        line = 2
    elif compact.startswith("DM"):
        line = 3
    elif compact.startswith("WB") or (
        compact.startswith("D") and not compact.startswith("DM")
    ):
        line = 4
    elif compact == "GK":
        line = 5
    else:
        line = 6
    side = (
        0
        if compact.endswith("L")
        else 1
        if compact.endswith("C")
        else 2
        if compact.endswith("R")
        else 3
    )
    return line, side


def rolePositionSortKey(role) -> tuple[int, int, str, str]:
    """Order a role using its earliest tactical position and stable role identity."""

    positionKeys = [positionSortKey(position) for position in role.positions]
    line, side = min(positionKeys, default=(6, 3))
    return line, side, role.displayName.casefold(), role.roleCode.casefold()
