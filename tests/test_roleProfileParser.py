import numpy as np

from fmsat.core.config import AttributeDefinition
from fmsat.core.ocr import OcrResult
from fmsat.core.parser import RoleProfileParser, TacticVocabulary
from fmsat.tests.conftest import FakeOcr


def _result(text: str, x: float, y: float, confidence: float = 0.99) -> OcrResult:
    return OcrResult(text, confidence, (x - 20, y - 5, x + 20, y + 5))


def testRoleProfileParserExtractsScreenshotFactsWithoutWeights() -> None:
    results = [
        _result("M (C)", 100, 30),
        _result("In Possession Role", 100, 50),
        _result("Central Midfielder", 150, 80),
        _result("Advanced Playmaker", 150, 120),
        _result("Channel Midfielder", 150, 160),
        _result("The Advanced Playmaker is a creative role", 650, 80),
        _result("Advanced Playmaker", 720, 110),
        _result("Role Ability", 620, 140),
        _result("which looks to operate high up the pitch", 650, 155),
        _result("between the opposition midfield and defence", 650, 170),
        _result("Key Attributes", 620, 180),
        _result("Off The Ball", 620, 220),
        _result("13", 900, 220),
        _result("Passing", 620, 250),
        _result("14", 900, 250),
        _result("Vision", 620, 280),
        _result("14", 900, 280),
        _result("Player Instructions", 620, 340),
        _result("Take More Risks", 620, 380),
    ]
    parser = RoleProfileParser(
        FakeOcr([results], suppliesGeometry=True),
        TacticVocabulary(),
        (
            AttributeDefinition("off_the_ball", "OtB", 1),
            AttributeDefinition("passing", "Pas", 2),
            AttributeDefinition("vision", "Vis", 3),
        ),
    )

    evidence = parser.parse(np.zeros((768, 1024, 3), dtype=np.uint8))

    assert evidence.position == "MC"
    assert evidence.phase.value == "inPossession"
    assert evidence.roleName == "Advanced Playmaker"
    assert evidence.abbreviation == "AP"
    assert evidence.keyAttributes == ("off_the_ball", "passing", "vision")
    assert evidence.displayedPlayerAttributes == {
        "off_the_ball": 13,
        "passing": 14,
        "vision": 14,
    }
    assert evidence.playerInstructions == ("takeMoreRisks",)
    assert evidence.description == (
        "which looks to operate high up the pitch " "between the opposition midfield and defence"
    )
    assert not hasattr(evidence, "weights")


def testRoleProfileParserRecognizesOutOfPossessionPhase() -> None:
    results = [
        _result("Out of Possession Role", 100, 40),
        _result("M (C)", 100, 60),
        _result("Advanced Playmaker", 720, 100),
        _result("Role Ability", 620, 140),
        _result("Key Attributes", 620, 180),
        _result("Passing", 620, 220),
    ]
    parser = RoleProfileParser(
        FakeOcr([results], suppliesGeometry=True),
        TacticVocabulary(),
        (AttributeDefinition("passing", "Pas", 1),),
    )

    evidence = parser.parse(np.zeros((768, 1024, 3), dtype=np.uint8))

    assert evidence.phase.value == "outOfPossession"
