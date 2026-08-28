"""Load the application QSS with its centrally declared colour palette."""

from __future__ import annotations

import re
from importlib.resources import files

_paletteBlock = re.compile(r"/\* FMSAT_PALETTE(?P<body>.*?)\*/", re.DOTALL)
_paletteEntry = re.compile(r"^\s*([a-z][a-zA-Z0-9]*)\s*:\s*(#[0-9a-fA-F]{6})\s*;\s*$")
_tokenPattern = re.compile(r"\{\{([a-z][a-zA-Z0-9]*)\}\}")


def stylePaletteLoad() -> dict[str, str]:
    """Return the centrally declared FMSAT palette as named colour values."""

    source = files("fmsat.app").joinpath("fmsat.qss").read_text(encoding="utf-8")
    match = _paletteBlock.search(source)
    if match is None:
        raise ValueError("fmsat.qss does not declare an FMSAT_PALETTE block")

    palette: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if not line.strip():
            continue
        entry = _paletteEntry.match(line)
        if entry is None:
            raise ValueError(f"invalid FMSAT palette declaration: {line.strip()}")
        palette[entry.group(1)] = entry.group(2)
    return palette


def styleSheetLoad() -> str:
    """Return the packaged QSS after resolving its named palette tokens."""

    source = files("fmsat.app").joinpath("fmsat.qss").read_text(encoding="utf-8")
    palette = stylePaletteLoad()

    def resolve(token: re.Match[str]) -> str:
        name = token.group(1)
        try:
            return palette[name]
        except KeyError as exc:
            raise ValueError(f"undefined FMSAT palette token: {name}") from exc

    return _tokenPattern.sub(resolve, source)