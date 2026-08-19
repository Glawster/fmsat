"""FM26 squad attribute header recovery regressions."""

from fmsat.core.ocr import OcrResult
from fmsat.core.parser.squadAttributesFm26 import SquadAttributesParser


class _OcrStub:
    suppliesGeometry = True


def testPhysicalHeadersInferBetweenTechniqueAndBalance() -> None:
    parser = SquadAttributesParser(_OcrStub(), {}, ())
    results = [
        OcrResult("Technique", 0.98, (80.0, 40.0, 120.0, 60.0)),
        OcrResult("Balance", 0.97, (380.0, 40.0, 420.0, 60.0)),
    ]

    acceleration = parser._attributeHeaderFind(results, "acceleration", 50.0, 15.0, 0.0)
    agility = parser._attributeHeaderFind(results, "agility", 50.0, 15.0, 0.0)

    assert acceleration is not None
    assert agility is not None
    assert acceleration.center is not None
    assert agility.center is not None
    assert acceleration.center[0] == 200.0
    assert agility.center[0] == 300.0


def testCaHeaderInfersFromRepeatedNumericColumnWhenHeadingIsDropped() -> None:
    parser = SquadAttributesParser(_OcrStub(), {}, ())
    results = [
        OcrResult("Position", 0.99, (280.0, 40.0, 340.0, 60.0)),
        OcrResult("PA", 0.99, (520.0, 40.0, 540.0, 60.0)),
        OcrResult("148", 0.98, (470.0, 90.0, 494.0, 108.0)),
        OcrResult("139", 0.98, (470.0, 120.0, 494.0, 138.0)),
        OcrResult("133", 0.98, (470.0, 150.0, 494.0, 168.0)),
    ]

    ca = parser._headerFind(results, "ca")

    assert ca is not None
    assert ca.center is not None
    assert ca.center[0] == 482.0


def testGoalkeeperColumnsUseStableSpacingAndRecoverTrailingHeaders() -> None:
    parser = SquadAttributesParser(_OcrStub(), {}, ())
    results = [
        OcrResult("Aerial Reach", 0.99, (780.0, 40.0, 820.0, 60.0)),
        OcrResult("Reflexes", 0.98, (1420.0, 40.0, 1460.0, 60.0)),
    ]

    eccentricity = parser._attributeHeaderFind(results, "eccentricity", 50.0, 15.0, 700.0)
    rushingOut = parser._attributeHeaderFind(results, "rushing_out", 50.0, 15.0, 700.0)
    throwing = parser._attributeHeaderFind(results, "throwing", 50.0, 15.0, 700.0)

    assert eccentricity is not None
    assert rushingOut is not None
    assert throwing is not None
    assert eccentricity.center is not None
    assert rushingOut.center is not None
    assert throwing.center is not None
    assert eccentricity.center[0] == 1040.0
    assert rushingOut.center[0] == 1580.0
    assert throwing.center[0] == 1660.0


def testPlayerNameCleanupCollapsesOverlappingStripDuplicate() -> None:
    assert (
        SquadAttributesParser._playerNameTextClean(
            "ARomane Enguehard Romane Engueharde"
        )
        == "Romane Enguehard"
    )
