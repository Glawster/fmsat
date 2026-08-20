"""Regression coverage for FM26 Natural Fitness header recovery."""

from fmsat.core.ocr import OcrResult
from fmsat.core.parser.squadAttributesFm26 import SquadAttributesParser


class _GeometryOcr:
    suppliesGeometry = True

    def recognize(self, _image):  # type: ignore[no-untyped-def]
        return []


def testNaturalFitnessCanBeInferredWithoutCapturingLongShots() -> None:
    parser = SquadAttributesParser(_GeometryOcr(), {}, ())
    results = [
        OcrResult("Jumping Reach", 0.96, (100, 10, 140, 30)),
        OcrResult("Long Shots", 0.94, (180, 10, 220, 30)),
    ]

    inferred = parser._attributeHeaderFind(
        results,
        "natural_fitness",
        headerY=20.0,
        tolerance=12.0,
        minimumX=0.0,
    )

    assert inferred is not None
    assert inferred.center is not None
    assert inferred.center[0] == 160.0
    assert inferred.text == "Natural Fitness (inferred)"
