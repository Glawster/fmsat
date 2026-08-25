"""OCR regression for a filtered seven-row squad attributes screenshot."""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import pytest
import yaml

from fmsat.core.config import Configuration
from fmsat.core.ocr import PaddleOcrEngine
from fmsat.core.parser import SquadAttributesParser
from fmsat.tests.test_squadScreenshotFixtures import (
    _attributeDifferences,
    _expectedNameResolve,
    _nameEquivalent,
    _positionEquivalent,
)


_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "squads" / "filteredSeven.yaml"
_SCREENSHOT = Path(__file__).parent / "screenshots" / "squads" / "filteredSeven" / "default1.png"


def _fixtureLoad() -> dict:
    content = yaml.safe_load(_FIXTURE_PATH.read_text(encoding="utf-8")) or {}
    assert isinstance(content, dict)
    return content


def _ocrEnabled() -> bool:
    return os.environ.get("FMSAT_OCR_FIXTURES", "").strip() == "1"


def _expectedAttributes(fixture: dict, playerName: str) -> dict[str, int]:
    columns = fixture["columnSets"]["default1"]["columns"]
    ignored = set(fixture["columnSets"]["default1"]["ignoredByFmsat"])
    values = fixture["players"][playerName]["default1"]
    return {
        str(column): int(value)
        for column, value in zip(columns, values, strict=True)
        if column not in ignored
    }


def testFilteredSevenFixtureContainsCanonicalScreenshot() -> None:
    fixture = _fixtureLoad()

    assert fixture["fixture"] == "filteredSeven"
    assert _SCREENSHOT.is_file()
    assert list(fixture["screenshots"]["default1.png"]["players"]) == [
        "Daniquie Tolhoek",
        "Laura Freigang",
        "Priscila",
        "Peta Trimis",
        "Libby Isaac",
        "Indie Power",
        "Alessia Russo",
    ]


@pytest.fixture(scope="module")
def squadOcrParser() -> SquadAttributesParser:
    configuration = Configuration()
    return SquadAttributesParser(
        PaddleOcrEngine(),
        configuration.regions,
        configuration.attributes,
    )


@pytest.mark.skipif(
    not _ocrEnabled(),
    reason="Set FMSAT_OCR_FIXTURES=1 to run real PaddleOCR screenshot regressions",
)
def testFilteredSevenScreenshotOcrExtractsAllSevenVisibleRows(
    squadOcrParser: SquadAttributesParser,
) -> None:
    """A filtered FM view with seven complete rows must parse like a full page."""

    fixture = _fixtureLoad()
    expectedNames = list(fixture["screenshots"]["default1.png"]["players"])
    image = cv2.imread(str(_SCREENSHOT))
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
            "filteredSeven/default1.png: expected "
            f"{len(expectedNames)} players, got {len(actualPlayers)}; "
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
            rowErrors.append(
                f"{expectedName} CA: expected={expected['ca']!r} actual={actual.ca!r}"
            )
        if actual.pa != str(expected["pa"]):
            rowErrors.append(
                f"{expectedName} PA: expected={expected['pa']!r} actual={actual.pa!r}"
            )
        for difference in _attributeDifferences(
            actual.attributes,
            _expectedAttributes(fixture, expectedName),
        ):
            rowErrors.append(f"{expectedName} {difference}")

    if rowErrors:
        pytest.fail("filteredSeven/default1.png OCR mismatches:\n" + "\n".join(rowErrors))
