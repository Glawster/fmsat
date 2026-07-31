"""Squad Attributes parser tests."""

import numpy as np

from fmsat.core.config import AttributeDefinition
from fmsat.core.ocr import OcrResult
from fmsat.core.parser import SquadAttributesParser
from fmsat.tests.conftest import FakeOcr


def testParserMapsAttributesByYamlDefinitionNotHardcodedOrder() -> None:
    # One row has name, positions, CA, PA, and one attribute. Three empty rows end parsing.
    ocr = FakeOcr(
        [
            [OcrResult("Ada Keeper", 0.99)],
            [OcrResult("GK", 0.98)],
            [OcrResult("3.5", 0.97)],
            [OcrResult("4", 0.96)],
            [OcrResult("17", 0.95)],
            *([[]] * 15),
        ]
    )
    regions = {
        "squadAttributes": {
            "table": {"x": 0, "y": 0, "width": 1, "height": 1},
            "header_height": 0,
            "row_height": 0.25,
            "columns": {
                "name": {"x": 0, "width": 0.2},
                "positions": {"x": 0.2, "width": 0.2},
                "ca": {"x": 0.4, "width": 0.1},
                "pa": {"x": 0.5, "width": 0.1},
            },
            "attribute_area": {"x": 0.6, "width": 0.4},
        }
    }
    parser = SquadAttributesParser(
        ocr,
        regions,
        (AttributeDefinition("reflexes", "Ref", 42),),
    )

    players = parser.parse(np.zeros((100, 100, 3), dtype=np.uint8))

    assert len(players) == 1
    assert players[0].name == "Ada Keeper"
    assert players[0].attributes == {"reflexes": 17}
    assert players[0].confidence == 0.97
