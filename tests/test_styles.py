from importlib.resources import files
import re

from fmsat.app.styles import styleSheetLoad


def testStyleSheetResolvesNamedPaletteTokens() -> None:
    stylesheet = styleSheetLoad()

    assert "{{" not in stylesheet
    assert "background: #101f2e" in stylesheet
    assert "QWidget#roleWeightImportant { background: #1a3044" in stylesheet


def testRawStyleSheetKeepsHexValuesInPaletteBlockOnly() -> None:
    source = files("fmsat.app").joinpath("fmsat.qss").read_text(encoding="utf-8")
    _prefix, declarations = source.split("*/", 1)

    assert re.search(r"#[0-9a-fA-F]{6}", declarations) is None
    assert "{{surface}}" in declarations
