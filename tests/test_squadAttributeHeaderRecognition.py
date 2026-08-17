"""Regression tests for FM squad-view attribute heading recognition."""

from fmsat.core.config import AttributeDefinition
from fmsat.core.ocr import OcrResult
from fmsat.core.parser import SquadAttributesParser
from fmsat.tests.conftest import FakeOcr


def _result(text: str, x: float, *, halfWidth: float = 10) -> OcrResult:
    return OcrResult(text, 0.99, (x - halfWidth, 16, x + halfWidth, 24))


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

    concentration = parser._attributeHeaderFind(results, "concentration", 20, 10, 0)
    offTheBall = parser._attributeHeaderFind(results, "off_the_ball", 20, 10, 0)

    assert concentration is not None
    assert concentration.text == "Concen..."
    assert offTheBall is not None
    assert offTheBall.text == "Off The ..."


def testSplitFirstTouchHeaderUsesCombinedColumnCentre() -> None:
    """A split FM header must not anchor First Touch on the word First alone."""

    parser = SquadAttributesParser(
        FakeOcr([]),
        {},
        (AttributeDefinition("first_touch", "Fir", 1),),
    )
    results = [
        _result("First", 100, halfWidth=18),
        _result("Touch", 145, halfWidth=19),
    ]

    header = parser._attributeHeaderFind(results, "first_touch", 20, 10, 0)

    assert header is not None
    assert header.text == "First Touch"
    assert header.center is not None
    assert 120 < header.center[0] < 130


def testSplitFirstTouchSurvivesInterleavedOcrFragment() -> None:
    """A neighbouring OCR fragment must not prevent the First Touch column being found."""

    parser = SquadAttributesParser(
        FakeOcr([]),
        {},
        (AttributeDefinition("first_touch", "Fir", 1),),
    )
    results = [
        _result("First", 100, halfWidth=18),
        _result("|", 120, halfWidth=2),
        _result("Touch", 145, halfWidth=19),
    ]

    header = parser._attributeHeaderFind(results, "first_touch", 20, 10, 0)

    assert header is not None
    assert header.text == "First Touch"


def testMissingFirstTouchHeaderIsInferredBetweenFinishingAndHeading() -> None:
    """FM's stable column order keeps First Touch available if OCR drops its heading."""

    parser = SquadAttributesParser(
        FakeOcr([]),
        {},
        (AttributeDefinition("first_touch", "Fir", 1),),
    )
    results = [
        _result("Finishing", 100),
        _result("Heading", 200),
    ]

    header = parser._attributeHeaderFind(results, "first_touch", 20, 10, 0)

    assert header is not None
    assert header.text == "First Touch (inferred)"
    assert header.center is not None
    assert header.center[0] == 150


def testPlayerNameCleanupDropsTrailingOcrPunctuation() -> None:
    parser = SquadAttributesParser(FakeOcr([]), {}, ())

    assert parser._playerNameTextClean("Georgia Stanway.") == "Georgia Stanway"
    assert parser._playerNameTextClean("Nerea Eizagirre,") == "Nerea Eizagirre"


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
