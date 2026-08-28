"""Shared colours for the FMSAT desktop interface."""

BUTTON = "#2563eb"
BUTTON_SELECTED = "#3b82f6"
BUTTON_BORDER = "#1d4ed8"
CELL_HEADER = BUTTON_SELECTED
CELL_HEADER_TEXT = "#ffffff"

# Formation bands from requirement 005. Keep these independent of role codes:
# a role takes the colour of the line in which it is being used.
FORMATION_ROWS = {
    "goalkeeper": "#4b4d70",
    "defence": "#0d7775",
    "defensiveMidfield": "#117b49",
    "midfield": "#174b85",
    "attackingMidfield": "#6d2089",
    "striker": "#981667",
}
FORMATION_UNKNOWN = "#475569"
