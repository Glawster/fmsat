"""Golden OCR regression coverage backed by canonical squad screenshots."""

from __future__ import annotations

import os
from pathlib import Path

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


def _ocrEnabled() -> bool:
    return os.environ.get("FMSAT_OCR_FIXTURES", "").strip() == "1"


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


def testBristolWomenFixtureContainsCanonicalScreenshots() -> None:
    fixture = _fixtureLoad()

    assert fixture["fixture"] == "bristolWomen"
    assert sorted(path.name for path in _SCREENSHOT_ROOT.glob("*.png")) == sorted(_SCREENSHOTS)
    assert set(fixture["screenshots"]) == set(_SCREENSHOTS)


def testBristolWomenFixtureCoversConfiguredSquadAttributes() -> None:
    fixture = _fixtureLoad()
    configured = {attribute.name for attribute in Configuration().attributes}
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
@pytest.mark.skipif(
    not _ocrEnabled(),
    reason="Set FMSAT_OCR_FIXTURES=1 to run real PaddleOCR screenshot regressions",
)
def testBristolWomenScreenshotOcrMatchesReviewedTruth(screenshotName: str) -> None:
    """Real OCR must reproduce every reviewed player fact visible on each canonical screenshot."""

    fixture = _fixtureLoad()
    screenshot = fixture["screenshots"][screenshotName]
    columnSet = str(screenshot["columnSet"])
    expectedNames = list(screenshot["players"])
    image = cv2.imread(str(_SCREENSHOT_ROOT / screenshotName))
    assert image is not None

    configuration = Configuration()
    parser = SquadAttributesParser(
        PaddleOcrEngine(),
        configuration.regions,
        configuration.attributes,
    )
    actualPlayers = parser.parse(image)

    assert [player.name for player in actualPlayers] == expectedNames
    assert len(actualPlayers) == len(expectedNames)
    for actual, expectedName in zip(actualPlayers, expectedNames, strict=True):
        expected = fixture["players"][expectedName]
        assert actual.name == expectedName
        assert actual.positions == str(expected["positions"])
        assert actual.ca == str(expected["ca"])
        assert actual.pa == str(expected["pa"])
        assert actual.attributes == _expectedAttributes(fixture, expectedName, columnSet)


@pytest.mark.skipif(
    not _ocrEnabled(),
    reason="Set FMSAT_OCR_FIXTURES=1 to run real PaddleOCR screenshot regressions",
)
def testBristolWomenFourSquadPagesMergeToReviewedThirtyEightPlayers() -> None:
    """The four outfield pages must merge without identity, CA/PA or attribute conflicts."""

    fixture = _fixtureLoad()
    configuration = Configuration()
    parser = SquadAttributesParser(
        PaddleOcrEngine(),
        configuration.regions,
        configuration.attributes,
    )
    merged: dict[str, dict[str, object]] = {}

    for screenshotName in ("squad1.png", "squad2.png", "squad3.png", "squad4.png"):
        image = cv2.imread(str(_SCREENSHOT_ROOT / screenshotName))
        assert image is not None
        for player in parser.parse(image):
            current = merged.setdefault(
                player.name,
                {
                    "positions": player.positions,
                    "ca": player.ca,
                    "pa": player.pa,
                    "attributes": {},
                },
            )
            assert current["positions"] == player.positions
            assert current["ca"] == player.ca
            assert current["pa"] == player.pa
            attributes = current["attributes"]
            assert isinstance(attributes, dict)
            for attribute, value in player.attributes.items():
                if attribute in attributes:
                    assert attributes[attribute] == value
                attributes[attribute] = value

    assert set(merged) == set(fixture["players"])
    assert len(merged) == 38
    for name, expected in fixture["players"].items():
        actual = merged[name]
        expectedAttributes = {
            **_expectedAttributes(fixture, name, "default1"),
            **_expectedAttributes(fixture, name, "default2"),
        }
        assert actual["positions"] == str(expected["positions"])
        assert actual["ca"] == str(expected["ca"])
        assert actual["pa"] == str(expected["pa"])
        assert actual["attributes"] == expectedAttributes
