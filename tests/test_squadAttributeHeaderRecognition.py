"""Regression tests for FM squad-view attribute heading recognition."""

from fmsat.core.config import AttributeDefinition
from fmsat.core.ocr import OcrResult
from fmsat.core.parser import SquadAttributesParser
from fmsat.tests.conftest import FakeOcr


def _result(text: str, x: float) -> OcrResult:
    return OcrResult(text, 0.99, (x - 10, 16, x + 10, 24))


def testCanonicalTruncatedHeadersRecogniseConcentrationAndOffTheBall() -> None:
    """FM headings, not FMSAT abbreviations, identify screenshot attribute columns."""

    parser = SquadAttributesParser(
        FakeOcr([]),
        {},
        (
            AttributeDefinition("concentration", "Cnt", 1),
            AttributeDefinition("off_the_ball", "OtB", 2),
        ),
    )
    results = [
        _result("Concen...", 100),
        _result("Off The ...", 200),
    ]

    concentration = parser._attributeHeaderFind(
        results,
        "concentration",
        20,
        10,
        0,
    )
    offTheBall = parser._attributeHeaderFind(
        results,
        "off_the_ball",
        20,
        10,
        0,
    )

    assert concentration is not None
    assert concentration.text == "Concen..."
    assert offTheBall is not None
    assert offTheBall.text == "Off The ..."


def testPresentationAbbreviationsAreNotAcceptedAsOcrHeaders() -> None:
    """Cnt and OtB remain presentation-only labels and never OCR identities."""

    parser = SquadAttributesParser(
        FakeOcr([]),
        {},
        (
            AttributeDefinition("concentration", "Cnt", 1),
            AttributeDefinition("off_the_ball", "OtB", 2),
        ),
    )
    results = [_result("Cnt", 100), _result("OtB", 200)]

    assert parser._attributeHeaderFind(results, "concentration", 20, 10, 0) is None
    assert parser._attributeHeaderFind(results, "off_the_ball", 20, 10, 0) is None
