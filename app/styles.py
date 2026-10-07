"""Load FMSAT QSS using the shared OMP application palette."""

from __future__ import annotations

import re
from importlib.resources import files

_localPaletteBlock = re.compile(r"/\* FMSAT_PALETTE(?P<body>.*?)\*/", re.DOTALL)
_localPaletteEntry = re.compile(
    r"^\s*([a-z][a-zA-Z0-9]*)\s*:\s*(#[0-9a-fA-F]{6})\s*;\s*$"
)
_sharedPaletteBlock = re.compile(
    r"Shared palette\s*-+\s*(?P<body>.*?)(?:\*/)", re.DOTALL
)
_sharedPaletteEntry = re.compile(
    r"^\s*([a-z][a-zA-Z0-9]*)\s*:\s*(#[0-9a-fA-F]{6})(?:\s+.*)?$"
)
_tokenPattern = re.compile(r"\{\{([a-z][a-zA-Z0-9]*)\}\}")


def _localPaletteLoad(source: str) -> dict[str, str]:
    """Return FMSAT-only fallback and specialist colour roles."""

    match = _localPaletteBlock.search(source)
    if match is None:
        raise ValueError("fmsat.qss does not declare an FMSAT_PALETTE block")

    palette: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if not line.strip():
            continue
        entry = _localPaletteEntry.match(line)
        if entry is None:
            raise ValueError(f"invalid FMSAT palette declaration: {line.strip()}")
        palette[entry.group(1)] = entry.group(2)
    return palette


def _sharedPaletteLoad() -> dict[str, str]:
    """Return the canonical application palette packaged by organiseMyProjects."""

    try:
        source = files("organiseMyProjects").joinpath("myStyles.css").read_text(
            encoding="utf-8"
        )
    except (ModuleNotFoundError, FileNotFoundError):
        return {}

    match = _sharedPaletteBlock.search(source)
    if match is None:
        return {}

    palette: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if not line.strip():
            continue
        entry = _sharedPaletteEntry.match(line)
        if entry is not None:
            palette[entry.group(1)] = entry.group(2)
    return palette


def stylePaletteLoad() -> dict[str, str]:
    """Return FMSAT colours with shared OMP semantic roles taking precedence."""

    source = files("fmsat.app").joinpath("fmsat.qss").read_text(encoding="utf-8")
    palette = _localPaletteLoad(source)
    shared = _sharedPaletteLoad()
    palette.update(shared)

    # OMP 0.8 introduces this shared hierarchy role. Keep a safe fallback for
    # environments which have not yet upgraded organiseMyProjects.
    palette.setdefault("surfaceRaised", palette.get("neutralSurface", "#243545"))
    return palette


def styleSheetLoad() -> str:
    """Return FMSAT QSS resolved against the shared OMP semantic palette."""

    source = files("fmsat.app").joinpath("fmsat.qss").read_text(encoding="utf-8")
    palette = stylePaletteLoad()

    # FMSAT keeps its widget-specific Qt selectors locally, while the colour
    # hierarchy comes from OMP. Validation phase rows are deliberately raised
    # above their containing validation panel.
    source += (
        "\nQFrame#validationPhase { background: {{surfaceRaised}}; "
        "border: 1px solid {{borderStrong}}; }\n"
    )

    def resolve(token: re.Match[str]) -> str:
        name = token.group(1)
        try:
            return palette[name]
        except KeyError as exc:
            raise ValueError(f"undefined FMSAT palette token: {name}") from exc

    return _tokenPattern.sub(resolve, source)
