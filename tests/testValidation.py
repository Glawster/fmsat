"""Player validation tests."""

from fmsat.core.parser import ExtractedPlayer
from fmsat.core.validation import PlayerValidator


def testLowConfidenceRowIsReported() -> None:
    player = ExtractedPlayer("Alex", "DM", "3", "4", {"passing": 15}, 0.94)

    issues = PlayerValidator(0.95).validate(player)

    assert [issue.field for issue in issues] == ["confidence"]


def testMissingNameAndInvalidAttributeAreReported() -> None:
    player = ExtractedPlayer("", "DM", "", "", {"passing": 21}, 1.0)

    issues = PlayerValidator().validate(player)

    assert {issue.field for issue in issues} == {"name", "passing"}
