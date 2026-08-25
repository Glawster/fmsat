import numpy as np
import pytest

from fmsat.core.config import AttributeDefinition
from fmsat.core.ocr import OcrResult
from fmsat.core.parser import RoleProfileParser, TacticVocabulary
from fmsat.core.parser.squadAttributes import ParserError
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


def testRoleProfileParserRecognizesCentralStrikerPosition() -> None:
    results = [
        _result("ST (C)", 100, 30),
        _result("In Possession Role", 100, 50),
        _result("Channel Forward", 720, 100),
        _result("Role Ability", 620, 140),
        _result("Key Attributes", 620, 180),
        _result("Finishing", 620, 220),
    ]
    parser = RoleProfileParser(
        FakeOcr([results], suppliesGeometry=True),
        TacticVocabulary(),
        (AttributeDefinition("finishing", "Fin", 1),),
    )

    evidence = parser.parse(np.zeros((768, 1024, 3), dtype=np.uint8))

    assert evidence.position == "STC"
    assert evidence.roleName == "Channel Forward"


def testRoleProfileParserPrefersRoleTitleOverAbilityRating() -> None:
    results = [
        _result("D (C)", 100, 30),
        _result("In Possession Role", 100, 50),
        _result("Ball-Playing Centre-Back", 720, 100),
        _result("Fairly Good", 800, 130),
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

    assert evidence.position == "DC"
    assert evidence.roleName == "Ball-Playing Centre-Back"
    assert evidence.abbreviation == "BCB"


def testRoleProfileParserCombinesSplitParenthesizedPosition() -> None:
    results = [
        _result("AM (", 80, 30),
        _result("C)", 120, 30),
        _result("In Possession Role", 100, 50),
        _result("Attacking Midfielder", 720, 100),
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

    assert evidence.position == "AMC"


def testRoleProfileParserCapturesAndDeduplicatesRoleIndicators() -> None:
    results = [
        _result("AM (L)", 100, 30),
        _result("In Possession Role", 100, 50),
        _result("Moves Inside", 650, 155),
        _result("Goal Threat", 760, 155),
        _result("Inside Forward", 720, 100),
        _result("Role Ability", 620, 140),
        _result("Moves Inside", 650, 155),
        _result("Goal Threat", 760, 155),
        _result("Key Attributes", 620, 180),
        _result("Off The Ball", 620, 220),
    ]
    parser = RoleProfileParser(
        FakeOcr([results], suppliesGeometry=True),
        TacticVocabulary(),
        (AttributeDefinition("off_the_ball", "OtB", 1),),
    )

    evidence = parser.parse(np.zeros((768, 1024, 3), dtype=np.uint8))

    assert evidence.behaviours == ("movesInside", "goalThreat")


def testRoleProfileParserExcludesBehaviourSummaryFromDescription() -> None:
    results = [
        _result("DM", 100, 30),
        _result("In Possession Role", 100, 50),
        _result("Moves Inside", 650, 154),
        _result("Goal Threat", 760, 154),
        _result("Box-To-Box Midfielder", 720, 100),
        _result("Role Ability", 620, 140),
        _result("Moves Inside Goal Threat", 700, 156),
        _result("The non-stop dynamism of the Box-to-Box Midfielder enables them", 700, 170),
        _result("to contribute greatly to both attacking play during the build-up", 700, 182),
        _result("and in the final third.", 700, 194),
        _result("Key Attributes", 620, 220),
        _result("Passing", 620, 240),
    ]
    parser = RoleProfileParser(
        FakeOcr([results], suppliesGeometry=True),
        TacticVocabulary(),
        (AttributeDefinition("passing", "Pas", 1),),
    )

    evidence = parser.parse(np.zeros((768, 1024, 3), dtype=np.uint8))

    assert evidence.behaviours == ("movesInside", "goalThreat")
    assert evidence.description is not None
    assert "Moves Inside Goal Threat" not in evidence.description
    assert "The non-stop dynamism" in evidence.description


def testRoleProfileParserIgnoresOtherRoleIndicatorsInLeftColumn() -> None:
    results = [
        _result("DM", 100, 30),
        _result("In Possession Role", 100, 50),
        _result("Careful", 180, 210),
        _result("Expressive", 180, 250),
        _result("Box-To-Box Midfielder", 720, 100),
        _result("Role Ability", 620, 140),
        _result("Moves Inside", 650, 154),
        _result("Goal Threat", 760, 154),
        _result("Key Attributes", 620, 220),
        _result("Passing", 620, 240),
    ]
    parser = RoleProfileParser(
        FakeOcr([results], suppliesGeometry=True),
        TacticVocabulary(),
        (AttributeDefinition("passing", "Pas", 1),),
    )

    evidence = parser.parse(np.zeros((768, 1024, 3), dtype=np.uint8))

    assert evidence.behaviours == ("movesInside", "goalThreat")


def testRoleProfileParserExtractsTwoIndicatorsFromCombinedLine() -> None:
    results = [
        _result("DM", 100, 30),
        _result("In Possession Role", 100, 50),
        _result("Box-To-Box Midfielder", 720, 100),
        _result("Role Ability", 620, 140),
        _result("Moves Back to CB Careful", 705, 148),
        _result("Key Attributes", 620, 220),
        _result("Passing", 620, 240),
    ]
    parser = RoleProfileParser(
        FakeOcr([results], suppliesGeometry=True),
        TacticVocabulary(),
        (AttributeDefinition("passing", "Pas", 1),),
    )

    evidence = parser.parse(np.zeros((768, 1024, 3), dtype=np.uint8))

    assert evidence.behaviours == ("movesBackToCB", "careful")


def testRoleProfileParserIgnoresLeftColumnTextAfterPlayerInstructionsHeading() -> None:
    results = [
        _result("DM", 100, 30),
        _result("Out of Possession Role", 100, 50),
        _result("Dropping Defensive Midfielder", 720, 100),
        _result("Role Ability", 620, 140),
        _result("Moves Back to CB", 705, 148),
        _result("Key Attributes", 620, 220),
        _result("Marking", 620, 240),
        _result("Player Instructions", 620, 340),
        _result("Wide Covering Defensive Midfielder", 180, 380),
        _result("Covers Flanks", 180, 400),
        _result("***", 650, 385),
    ]
    parser = RoleProfileParser(
        FakeOcr([results], suppliesGeometry=True),
        TacticVocabulary(),
        (AttributeDefinition("marking", "Mar", 1),),
    )

    evidence = parser.parse(np.zeros((768, 1024, 3), dtype=np.uint8))

    assert evidence.playerInstructions == ()


def _fallbackParser(results: list[OcrResult]) -> RoleProfileParser:
    names = (
        "heading",
        "marking",
        "passing",
        "tackling",
        "anticipation",
        "positioning",
        "strength",
        "jumping_reach",
    )
    return RoleProfileParser(
        FakeOcr([results], suppliesGeometry=True),
        TacticVocabulary(),
        tuple(AttributeDefinition(name, name[:3], index) for index, name in enumerate(names)),
    )


def _roleProfileWithoutKeyHeading(
    attributeY: float,
    includeInstructions: bool = True,
) -> list[OcrResult]:
    results = [
        _result("D (C)", 100, 30),
        _result("In Possession Role", 100, 50),
        _result("Ball-Playing Centre-Back", 720, 80),
        _result("Role Ability", 620, 110),
        _result("A description whose height is controlled by its content", 680, attributeY - 30),
    ]
    for offset, name in enumerate(
        (
            "Heading",
            "Marking",
            "Passing",
            "Tackling",
            "Anticipation",
            "Positioning",
            "Strength",
            "Jumping Reach",
        )
    ):
        y = attributeY + offset * 24
        results.extend((_result(name, 620, y), _result(str(11 + offset % 8), 900, y)))
    if includeInstructions:
        results.extend(
            (
                _result("Player Instructions", 620, attributeY + 8 * 24 + 10),
                _result("Marking", 620, attributeY + 9 * 24),
                _result("20", 900, attributeY + 9 * 24),
            )
        )
    return results


@pytest.mark.parametrize("headingY", [115, 180])
def testRoleProfileParserUsesRecognizedKeyAttributesHeadingAtAnyHeight(
    headingY: float,
) -> None:
    results = _roleProfileWithoutKeyHeading(headingY + 25)
    results.insert(5, _result("Key Attributes", 620, headingY))

    evidence = _fallbackParser(results).parse(np.zeros((768, 1024, 3), dtype=np.uint8))

    assert evidence.keyAttributes[0] == "heading"
    assert len(evidence.keyAttributes) == 8


@pytest.mark.parametrize("attributeY", [165, 330])
def testRoleProfileParserRecoversMissingHeadingIndependentOfDescriptionPosition(
    attributeY: float,
) -> None:
    results = _roleProfileWithoutKeyHeading(attributeY)

    evidence = _fallbackParser(results).parse(np.zeros((768, 1024, 3), dtype=np.uint8))

    assert evidence.keyAttributes == (
        "heading",
        "marking",
        "passing",
        "tackling",
        "anticipation",
        "positioning",
        "strength",
        "jumping_reach",
    )
    assert evidence.displayedPlayerAttributes["jumping_reach"] == 18


def testRoleProfileParserBoundsMissingHeadingFallbackAtPlayerInstructions() -> None:
    evidence = _fallbackParser(_roleProfileWithoutKeyHeading(180)).parse(
        np.zeros((768, 1024, 3), dtype=np.uint8)
    )

    assert evidence.displayedPlayerAttributes["marking"] == 12


def testRoleProfileParserDoesNotUseLeftRoleListAttributesForFallback() -> None:
    results = _roleProfileWithoutKeyHeading(180)
    results[5:9] = [
        _result("Heading", 180, 130),
        _result("20", 280, 130),
        _result("Marking", 180, 154),
        _result("20", 280, 154),
    ]

    evidence = _fallbackParser(results).parse(np.zeros((768, 1024, 3), dtype=np.uint8))

    assert "heading" not in evidence.keyAttributes
    assert "marking" not in evidence.keyAttributes


def testRoleProfileParserRejectsInsufficientMissingHeadingEvidence() -> None:
    results = _roleProfileWithoutKeyHeading(180)
    del results[9:]

    with pytest.raises(ParserError, match="credible attribute block"):
        _fallbackParser(results).parse(np.zeros((768, 1024, 3), dtype=np.uint8))
