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
            [OcrResult(" .- Ada Keeper", 0.99)],
            [OcrResult("- GK", 0.98)],
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
    assert players[0].positions == "GK"
    assert players[0].attributes == {"reflexes": 17}
    assert players[0].confidence == 0.97


def testParserUsesHeadersAndOcrBoxesInsteadOfFixedRowSteps() -> None:
    def result(
        text: str,
        x: float,
        y: float,
        confidence: float = 0.99,
    ) -> OcrResult:
        return OcrResult(text, confidence, (x - 8, y - 4, x + 8, y + 4))

    ocr = FakeOcr(
        [
            [
                result("Position", 250, 100),
                result("CA", 380, 100),
                result("PA", 430, 100),
                result("Cro...", 500, 100),
                result("Max Power", 120, 140),
                result("DM, M (C)", 250, 140),
                result("114", 380, 140),
                result("130", 430, 140),
                result("13", 500, 140),
                result("Joe Wright", 120, 179),
                result("D (C)", 250, 179),
                result("112", 380, 179),
                result("118", 430, 179),
                result("7", 500, 179),
            ]
        ],
        suppliesGeometry=True,
    )
    parser = SquadAttributesParser(
        ocr,
        {"squadAttributes": {}},
        (AttributeDefinition("crossing", "Cro", 1),),
    )

    players = parser.parse(np.zeros((400, 800, 3), dtype=np.uint8))

    assert [player.name for player in players] == ["Max Power", "Joe Wright"]
    assert [player.positions for player in players] == ["DM, M (C)", "D (C)"]
    assert [player.ca for player in players] == ["114", "112"]
    assert [player.attributes for player in players] == [
        {"crossing": 13},
        {"crossing": 7},
    ]


def testParserMergesDenseScreenshotStripsWithoutDuplicatingOverlap() -> None:
    def result(text: str, x: float, y: float) -> OcrResult:
        return OcrResult(text, 0.99, (x - 8, y - 4, x + 8, y + 4))

    firstResults = [
        result("Position", 250, 100),
        result("CA", 380, 100),
        result("PA", 430, 100),
        result("Max Power", 120, 200),
        result("DM", 250, 200),
        result("114", 380, 200),
        result("130", 430, 200),
    ]
    secondResults = [
        result("Shared Player", 120, 284),
        result("D (C)", 250, 284),
        result("105", 380, 284),
        result("120", 430, 284),
    ]
    thirdResults = [
        result("Shared Player", 120, 84),
        result("D (C)", 250, 84),
        result("105", 380, 84),
        result("120", 430, 84),
        result("Lower Player", 120, 264),
        result("ST (C)", 250, 264),
        result("100", 380, 264),
        result("110", 430, 264),
    ]
    fourthResults = [
        result("Lower Player", 120, 64),
        result("ST (C)", 250, 64),
        result("100", 380, 64),
        result("110", 430, 64),
    ]
    parser = SquadAttributesParser(
        FakeOcr(
            [firstResults, secondResults, thirdResults, fourthResults],
            suppliesGeometry=True,
        ),
        {"squadAttributes": {}},
        (),
    )

    players = parser.parse(np.zeros((800, 1400, 3), dtype=np.uint8))

    assert [player.name for player in players] == [
        "Max Power",
        "Shared Player",
        "Lower Player",
    ]
