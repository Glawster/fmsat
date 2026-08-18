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

    def ocrResult(
        text: str,
        x: float,
        y: float,
        confidence: float = 0.99,
    ) -> OcrResult:
        return OcrResult(text, confidence, (x - 8, y - 4, x + 8, y + 4))

    ocr = FakeOcr(
        [
            [
                ocrResult("Position", 250, 100),
                ocrResult("Player", 80, 100),
                ocrResult("CA", 380, 100),
                ocrResult("PA", 430, 100),
                ocrResult("Cro...", 500, 100),
                ocrResult("O", 82, 140),
                ocrResult("eMax Power", 120, 140),
                ocrResult("DM, M (C)", 250, 140),
                ocrResult("114", 380, 140),
                ocrResult("130", 430, 140),
                ocrResult("13", 500, 140),
                ocrResult("Joe Wright", 120, 179),
                ocrResult("D (C)", 250, 179),
                ocrResult("112", 380, 179),
                ocrResult("118", 430, 179),
                ocrResult("7", 500, 179),
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


def testParserKeepsFullTableNamesWhenFocusedOcrFragmentsCoverOneRow() -> None:

    def ocrResult(text: str, x: float, y: float) -> OcrResult:
        return OcrResult(text, 0.99, (x - 8, y - 4, x + 8, y + 4))

    fullResults = [
        ocrResult("Player", 80, 20),
        ocrResult("Position", 250, 20),
        ocrResult("CA", 380, 20),
        ocrResult("PA", 430, 20),
    ]
    for name, y, ca, pa in (
        ("George Goodman", 60, "75", "123"),
        ("Lewis Boney", 100, "65", "112"),
        ("Jack Ryder", 140, "43", "81"),
    ):
        fullResults.extend(
            (
                ocrResult(name, 120, y),
                ocrResult("D (C)", 250, y),
                ocrResult(ca, 380, y),
                ocrResult(pa, 430, y),
            )
        )
    focusedFragments = [
        ocrResult("George", 40, 20),
        ocrResult("Good", 80, 20),
        ocrResult("man", 120, 20),
    ]
    parser = SquadAttributesParser(
        FakeOcr([fullResults, focusedFragments], suppliesGeometry=True),
        {"squadAttributes": {}},
        (),
    )

    players = parser.parse(np.zeros((400, 800, 3), dtype=np.uint8))

    assert [player.name for player in players] == [
        "George Goodman",
        "Lewis Boney",
        "Jack Ryder",
    ]


def testParserMergesDenseScreenshotStripsWithoutDuplicatingOverlap() -> None:

    def ocrResult(text: str, x: float, y: float) -> OcrResult:
        scale = 1.5
        return OcrResult(
            text,
            0.99,
            (
                (x - 8) * scale,
                (y - 4) * scale,
                (x + 8) * scale,
                (y + 4) * scale,
            ),
        )

    firstResults = [
        ocrResult("Position", 250, 100),
        ocrResult("CA", 380, 100),
        ocrResult("PA", 430, 100),
        ocrResult("Max Power", 120, 200),
        ocrResult("DM", 250, 200),
        ocrResult("114", 380, 200),
        ocrResult("130", 430, 200),
    ]
    secondResults = [
        ocrResult("Shared Player", 120, 284),
        ocrResult("D (C)", 250, 284),
        ocrResult("105", 380, 284),
        ocrResult("120", 430, 284),
    ]
    thirdResults = [
        ocrResult("Shared Player", 120, 84),
        ocrResult("D (C)", 250, 84),
        ocrResult("105", 380, 84),
        ocrResult("120", 430, 84),
        ocrResult("Lower Player", 120, 264),
        ocrResult("ST (C)", 250, 264),
        ocrResult("100", 380, 264),
        ocrResult("110", 430, 264),
    ]
    fourthResults = [
        ocrResult("Lower Player", 120, 64),
        ocrResult("ST (C)", 250, 64),
        ocrResult("100", 380, 64),
        ocrResult("110", 430, 64),
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
