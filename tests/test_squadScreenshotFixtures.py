"""Golden OCR regression coverage backed by canonical squad screenshots."""

from __future__ import annotations

from pathlib import Path
import re
import unicodedata

import cv2
import pytest
import yaml

from fmsat.core.config import Configuration
from fmsat.core.ocr import PaddleOcrEngine
from fmsat.core.parser import SquadAttributesParser

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "squads" / "bristolWomen.yaml"
_SCREENSHOT_ROOT = Path(__file__).parent / "screenshots" / "squads" / "bristolWomen"
_SCREENSHOTS = ("squad1.png", "squad2.png", "squad3.png", "squad4.png", "goalkeeper.png")


def _fixtureLoad() -> dict:
    content = yaml.safe_load(_FIXTURE_PATH.read_text(encoding="utf-8")) or {}
    assert isinstance(content, dict)
    return content


@pytest.fixture(scope="module")
def squadOcrParser() -> SquadAttributesParser:
    configuration = Configuration()
    return SquadAttributesParser(
        PaddleOcrEngine(),
        configuration.regions,
        configuration.activeAttributes,
    )


def _expectedAttributes(fixture: dict, playerName: str, columnSet: str) -> dict[str, int]:
    columns = fixture["columnSets"][columnSet]["columns"]
    ignored = set(fixture["columnSets"][columnSet]["ignoredByFmsat"])
    values = fixture["players"][playerName][columnSet]
    assert len(columns) == len(values)
    return {
        str(column): int(value)
        for column, value in zip(columns, values, strict=True)
        if column not in ignored
    }


def _nameComparable(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(
        character.casefold()
        for character in decomposed
        if not unicodedata.combining(character) and character.isalnum()
    )


def _editDistanceAtMost(left: str, right: str, limit: int = 2) -> bool:
    """Allow a very small raw-OCR spelling error without changing reviewed identity truth."""

    if left == right:
        return True
    if abs(len(left) - len(right)) > limit:
        return False
    previous = list(range(len(right) + 1))
    for leftIndex, leftCharacter in enumerate(left, start=1):
        current = [leftIndex]
        rowMinimum = current[0]
        for rightIndex, rightCharacter in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[rightIndex] + 1,
                    previous[rightIndex - 1] + (leftCharacter != rightCharacter),
                )
            )
            rowMinimum = min(rowMinimum, current[-1])
        if rowMinimum > limit:
            return False
        previous = current
    return previous[-1] <= limit


def _nameEquivalent(actual: str, expected: str) -> bool:
    return _editDistanceAtMost(_nameComparable(actual), _nameComparable(expected))


def _positionComparable(value: str) -> str:
    """Compare OCR position semantics while ignoring punctuation, spacing and letter case."""

    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _positionEquivalent(actual: str, expected: str) -> bool:
    return _positionComparable(actual) == _positionComparable(expected)


def _expectedNameResolve(fixture: dict, actualName: str, ca: str, pa: str) -> str:
    matches = [
        name
        for name, values in fixture["players"].items()
        if _nameEquivalent(actualName, name) and str(values["ca"]) == ca and str(values["pa"]) == pa
    ]
    assert len(matches) == 1, f"Unable to resolve OCR player identity: {actualName!r}"
    return str(matches[0])


def _attributeDifferences(
    actual: dict[str, int | None],
    expected: dict[str, int],
) -> list[str]:
    differences = []
    for attribute in sorted(set(actual) | set(expected)):
        actualValue = actual.get(attribute, "<missing>")
        expectedValue = expected.get(attribute, "<not expected>")
        if actualValue != expectedValue:
            differences.append(f"{attribute}: expected={expectedValue!r} actual={actualValue!r}")
    return differences


def testBristolWomenFixtureContainsCanonicalScreenshots() -> None:
    fixture = _fixtureLoad()

    assert fixture["fixture"] == "bristolWomen"
    assert sorted(path.name for path in _SCREENSHOT_ROOT.glob("*.png")) == sorted(_SCREENSHOTS)
    assert set(fixture["screenshots"]) == set(_SCREENSHOTS)


def testBristolWomenFixtureCoversConfiguredSquadAttributes() -> None:
    fixture = _fixtureLoad()
    configured = {attribute.name for attribute in Configuration().activeAttributes}
    represented = {
        str(column)
        for columnSet in fixture["columnSets"].values()
        for column in columnSet["columns"]
        if column not in set(columnSet["ignoredByFmsat"])
    }

    assert represented == configured
    assert fixture["columnSets"]["default1"]["ignoredByFmsat"] == ["long_shots"]
    assert fixture["columnSets"]["default2"]["ignoredByFmsat"] == ["bravery"]


def testBristolWomenFixtureDefinesThirtyEightDistinctPlayersAndFourGoalkeepers() -> None:
    fixture = _fixtureLoad()
    players = fixture["players"]
    firstPage = set(fixture["screenshots"]["squad1.png"]["players"])
    secondPage = set(fixture["screenshots"]["squad2.png"]["players"])
    goalkeepers = fixture["screenshots"]["goalkeeper.png"]["players"]

    assert len(players) == 38
    assert len(firstPage | secondPage) == 38
    assert firstPage & secondPage == {
        "Peta Trimis",
        "Marisa Olislagers",
        "Laura Blindkilde Brown",
        "Fran Bentley",
    }
    assert goalkeepers == [
        "Selma Panengstuen",
        "Gabi Barbieri",
        "Fran Bentley",
        "Lauren Brzykcy",
    ]
    assert all(players[name]["positions"] == "GK" for name in goalkeepers)
    assert all("goalkeeper" in players[name] for name in goalkeepers)


@pytest.mark.parametrize("screenshotName", _SCREENSHOTS)
@pytest.mark.expensive
def testBristolWomenScreenshotOcrMatchesReviewedTruth(
    screenshotName: str,
    squadOcrParser: SquadAttributesParser,
) -> None:
    """Real OCR must reproduce every reviewed player fact visible on each canonical screenshot."""

    fixture = _fixtureLoad()
    screenshot = fixture["screenshots"][screenshotName]
    columnSet = str(screenshot["columnSet"])
    expectedNames = list(screenshot["players"])
    image = cv2.imread(str(_SCREENSHOT_ROOT / screenshotName))
    assert image is not None

    actualPlayers = squadOcrParser.parse(image)
    actualNames = [player.name for player in actualPlayers]

    if len(actualPlayers) != len(expectedNames):
        resolved = []
        unresolved = []
        for player in actualPlayers:
            try:
                resolved.append(_expectedNameResolve(fixture, player.name, player.ca, player.pa))
            except AssertionError:
                unresolved.append(player.name)
        missing = [name for name in expectedNames if name not in resolved]
        extra = [name for name in resolved if name not in expectedNames]
        pytest.fail(
            f"{screenshotName}: expected {len(expectedNames)} players, got {len(actualPlayers)}; "
            f"missing={missing}; extra={extra}; unresolved={unresolved}; actual={actualNames}"
        )

    rowErrors = []
    for rowIndex, (actual, expectedName) in enumerate(
        zip(actualPlayers, expectedNames, strict=True),
        start=1,
    ):
        expected = fixture["players"][expectedName]
        if not _nameEquivalent(actual.name, expectedName):
            rowErrors.append(
                f"row {rowIndex} name: expected={expectedName!r} actual={actual.name!r}"
            )
        if not _positionEquivalent(actual.positions, str(expected["positions"])):
            rowErrors.append(
                f"{expectedName} positions: expected={expected['positions']!r} actual={actual.positions!r}"
            )
        if actual.ca != str(expected["ca"]):
            rowErrors.append(f"{expectedName} CA: expected={expected['ca']!r} actual={actual.ca!r}")
        if actual.pa != str(expected["pa"]):
            rowErrors.append(f"{expectedName} PA: expected={expected['pa']!r} actual={actual.pa!r}")
        expectedAttributes = _expectedAttributes(fixture, expectedName, columnSet)
        for difference in _attributeDifferences(actual.attributes, expectedAttributes):
            rowErrors.append(f"{expectedName} {difference}")

    if rowErrors:
        pytest.fail(f"{screenshotName} OCR mismatches:\n" + "\n".join(rowErrors))


@pytest.mark.expensive
def testBristolWomenFourSquadPagesMergeToReviewedThirtyEightPlayers(
    squadOcrParser: SquadAttributesParser,
) -> None:
    """The four outfield pages must merge without identity, CA/PA or attribute conflicts."""

    fixture = _fixtureLoad()
    merged: dict[str, dict[str, object]] = {}
    mergeErrors = []

    for screenshotName in ("squad1.png", "squad2.png", "squad3.png", "squad4.png"):
        image = cv2.imread(str(_SCREENSHOT_ROOT / screenshotName))
        assert image is not None
        for player in squadOcrParser.parse(image):
            canonicalName = _expectedNameResolve(fixture, player.name, player.ca, player.pa)
            current = merged.setdefault(
                canonicalName,
                {
                    "positions": player.positions,
                    "ca": player.ca,
                    "pa": player.pa,
                    "attributes": {},
                    "sources": {},
                },
            )
            if not _positionEquivalent(str(current["positions"]), player.positions):
                mergeErrors.append(
                    f"{canonicalName} positions conflict in {screenshotName}: "
                    f"existing={current['positions']!r} actual={player.positions!r}"
                )
            if current["ca"] != player.ca:
                mergeErrors.append(
                    f"{canonicalName} CA conflict in {screenshotName}: "
                    f"existing={current['ca']!r} actual={player.ca!r}"
                )
            if current["pa"] != player.pa:
                mergeErrors.append(
                    f"{canonicalName} PA conflict in {screenshotName}: "
                    f"existing={current['pa']!r} actual={player.pa!r}"
                )
            attributes = current["attributes"]
            sources = current["sources"]
            assert isinstance(attributes, dict)
            assert isinstance(sources, dict)
            for attribute, value in player.attributes.items():
                if attribute in attributes and attributes[attribute] != value:
                    mergeErrors.append(
                        f"{canonicalName} {attribute} conflict: "
                        f"{sources[attribute]}={attributes[attribute]!r}, "
                        f"{screenshotName}={value!r}"
                    )
                elif attribute not in attributes or attributes[attribute] is None:
                    attributes[attribute] = value
                    sources[attribute] = screenshotName

    missingPlayers = sorted(set(fixture["players"]) - set(merged))
    extraPlayers = sorted(set(merged) - set(fixture["players"]))
    if missingPlayers or extraPlayers:
        mergeErrors.append(
            f"merged player identity mismatch: missing={missingPlayers}; extra={extraPlayers}"
        )

    for name, expected in fixture["players"].items():
        if name not in merged:
            continue
        actual = merged[name]
        expectedAttributes = {
            **_expectedAttributes(fixture, name, "default1"),
            **_expectedAttributes(fixture, name, "default2"),
        }
        if not _positionEquivalent(str(actual["positions"]), str(expected["positions"])):
            mergeErrors.append(
                f"{name} merged positions: expected={expected['positions']!r} actual={actual['positions']!r}"
            )
        if actual["ca"] != str(expected["ca"]):
            mergeErrors.append(
                f"{name} merged CA: expected={expected['ca']!r} actual={actual['ca']!r}"
            )
        if actual["pa"] != str(expected["pa"]):
            mergeErrors.append(
                f"{name} merged PA: expected={expected['pa']!r} actual={actual['pa']!r}"
            )
        attributes = actual["attributes"]
        assert isinstance(attributes, dict)
        for difference in _attributeDifferences(attributes, expectedAttributes):
            mergeErrors.append(f"{name} merged {difference}")

    if mergeErrors:
        pytest.fail("Merged squad OCR mismatches:\n" + "\n".join(mergeErrors))