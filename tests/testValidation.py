"""Player validation tests."""

from unittest.mock import Mock

from fmsat.core.parser import ExtractedPlayer
from fmsat.core.validation import PlayerValidator
from fmsat.core.validation import player as playerValidation


def testLowConfidenceRowIsReported() -> None:
    player = ExtractedPlayer("Alex Example", "DM", "3", "4", {"passing": 15}, 0.94)

    issues = PlayerValidator(0.95).validate(player)

    assert [issue.field for issue in issues] == ["confidence"]


def testMissingNameAndInvalidAttributeAreReported() -> None:
    player = ExtractedPlayer("", "DM", "", "", {"passing": 21}, 1.0)

    issues = PlayerValidator().validate(player)

    assert {issue.field for issue in issues} == {"name", "ca", "pa", "passing"}
    assert all(issue.blocking for issue in issues)


def testSafeOcrCorrectionsAreAppliedAndLogged(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    auditLogger = Mock()
    monkeypatch.setattr(playerValidation, "logger", auditLogger)
    players = [
        ExtractedPlayer(
            "  DJoe Hilton. ",
            "gk",
            " 84 ",
            " 110 ",
            {"passing": 8},
            0.98,
        )
    ]

    report = PlayerValidator().correctAll(players, context="test capture")

    assert report.players[0].name == "Joe Hilton"
    assert report.players[0].positions == "GK"
    assert report.players[0].ca == "84"
    assert report.players[0].pa == "110"
    assert {item.field for item in report.corrections} == {
        "name",
        "positions",
        "ca",
        "pa",
    }
    assert auditLogger.action.call_count == 4


def testRepeatedIconContaminatedNameIsCorrected() -> None:
    player = ExtractedPlayer(
        "Oe Ethan Wheatley Qe Ethan Wheatley",
        "AM (RL), ST (C)",
        "100",
        "121",
        {},
        0.98,
    )

    report = PlayerValidator().correctAll([player], context="test capture")

    assert report.players[0].name == "Ethan Wheatley"


def testMalformedAndDuplicateRowsAreBlocking() -> None:
    players = [
        ExtractedPlayer("Max Power", "DM, M (C)", "114", "130", {}, 0.98),
        ExtractedPlayer("Max Power", "DM, M (C)", "114", "130", {}, 0.98),
        ExtractedPlayer(
            "Paul Mullin Stephen Humphrys",
            "ST (C)",
            "107 109",
            "120 130",
            {},
            0.98,
        ),
    ]

    report = PlayerValidator().correctAll(players, context="test capture")

    messages = [issue.message for _, issue in report.blockingIssues]
    assert "Possible duplicate of row 1" in messages
    assert "CA must be one integer" in messages
    assert "PA must be one integer" in messages


def testMissingDataReportIdentifiesAffectedPlayers() -> None:
    players = [
        ExtractedPlayer("Max Power", "DM", "114", "130", {"passing": None}, 0.98),
        ExtractedPlayer("Joe Wright", "D (C)", "112", "118", {"passing": 12}, 0.98),
    ]

    report = PlayerValidator().correctAll(players, context="test capture")

    assert report.missingPlayers == (0,)
    assert report.missingByPlayer == ((0, "Max Power", ("passing",)),)


def testExactDuplicateRowsMergeComplementaryAttributes() -> None:
    players = [
        ExtractedPlayer("Max Power", "DM", "114", "130", {"passing": 15}, 0.96),
        ExtractedPlayer("Max Power", "DM", "114", "130", {"vision": 16}, 0.99),
    ]

    merged, count = PlayerValidator().duplicatesMerge(players, context="test")

    assert count == 1
    assert len(merged) == 1
    assert merged[0].attributes == {"passing": 15, "vision": 16}
    assert merged[0].confidence == 0.99


def testObviousNameAndAbilityOcrArtifactsAreCorrected() -> None:
    player = ExtractedPlayer(
        "De Thomas cissa",
        "D (C)",
        "f2 42",
        "82",
        {},
        0.98,
    )

    report = PlayerValidator().correctAll([player], context="test")

    assert report.players[0].name == "Thomas Cissa"
    assert report.players[0].ca == "42"


def testDuplicatedAbilityUsesFinalValueOnlyForSimplePlayerName() -> None:
    simple = ExtractedPlayer(
        "Stephen Humphrys", "AM (RLC), ST (C)", "109", "130 120", {}, 0.98
    )
    composite = ExtractedPlayer(
        "Paul Mullin Stephen Humphrys",
        "AM (RLC), ST (C)",
        "107 109",
        "120 130",
        {},
        0.97,
    )

    report = PlayerValidator().correctAll([simple, composite], context="test")

    assert report.players[0].pa == "120"
    assert report.players[1].ca == "107 109"
    assert report.players[1].pa == "120 130"


def testPlayerNameMustContainExactlyTwoWords() -> None:
    issues = PlayerValidator().validate(
        ExtractedPlayer("Curtis Tilt Matthew Pennington", "D (C)", "105", "125", {}, 0.98)
    )

    assert any(
        issue.message == "Player name must contain a first name and surname"
        and issue.blocking
        for issue in issues
    )
