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
