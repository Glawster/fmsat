"""Screenshot import service tests."""

from unittest.mock import Mock

import numpy as np

from fmsat.core.detection import ScreenType
from fmsat.core.parser import ExtractedPlayer
from fmsat.core.services import ImportResult, ScreenshotImportService, squadCapturesMerge


def testRequestedInstructionTypeWinsWhenInstructionDetectionIsAmbiguous() -> None:

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    preprocessor = Mock()
    preprocessor.process.return_value = image
    detector = Mock()
    detector.detect.return_value = ScreenType.TACTIC_IN_POSSESSION
    service = ScreenshotImportService(preprocessor, detector, Mock(), Mock())

    result = service.imageImport(
        image,
        ScreenType.TACTIC_OUT_OF_POSSESSION,
        "clipboard",
    )

    assert result.screenType is ScreenType.TACTIC_OUT_OF_POSSESSION


def testRequestedSquadTypeIsValidatedByRowExtractionWhenDetectionIsUnknown() -> None:

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    preprocessor = Mock()
    preprocessor.process.return_value = image
    detector = Mock()
    detector.detect.return_value = ScreenType.UNKNOWN
    squadParser = Mock()
    squadParser.parse.return_value = [
        ExtractedPlayer("Max Power", "DM, M (C)", "114", "130", {}, 0.98)
    ]
    service = ScreenshotImportService(preprocessor, detector, squadParser, Mock())

    result = service.imageImport(image, ScreenType.SQUAD_ATTRIBUTES, "clipboard")

    assert result.screenType is ScreenType.SQUAD_ATTRIBUTES
    assert [player.name for player in result.players] == ["Max Power"]


def testComplementarySquadCapturesMergePlayersAndAttributes() -> None:

    first = ImportResult(
        "first",
        ScreenType.SQUAD_ATTRIBUTES,
        [ExtractedPlayer("Max Power", "DM", "114", "130", {"passing": 15}, 0.98)],
        image=np.zeros((10, 10, 3), dtype=np.uint8),
    )
    second = ImportResult(
        "second",
        ScreenType.SQUAD_ATTRIBUTES,
        [ExtractedPlayer("Max Power", "DM", "114", "130", {"vision": 16}, 0.97)],
        image=np.ones((10, 10, 3), dtype=np.uint8),
    )

    merged = squadCapturesMerge(first, second)

    assert len(merged.players) == 1
    assert merged.players[0].attributes == {"passing": 15, "vision": 16}
    assert len(merged.additionalImages) == 1
    assert merged.mergeConflicts == []


def testComplementaryCaptureReconcilesOcrNameFragment() -> None:
    first = ImportResult(
        "first",
        ScreenType.SQUAD_ATTRIBUTES,
        [ExtractedPlayer("Smith, Qe Ella", "M (C)", "105", "125", {"passing": 14}, 0.82)],
    )
    second = ImportResult(
        "second",
        ScreenType.SQUAD_ATTRIBUTES,
        [ExtractedPlayer("Smith, Ella", "M (C)", "105", "125", {"vision": 13}, 0.97)],
    )

    merged = squadCapturesMerge(first, second)

    assert len(merged.players) == 1
    assert merged.players[0].name == "Smith, Ella"


def testComplementarySquadCaptureConflictsAreReported() -> None:

    first = ImportResult(
        "first",
        ScreenType.SQUAD_ATTRIBUTES,
        [ExtractedPlayer("Max Power", "DM", "114", "130", {"passing": 15}, 0.98)],
    )
    second = ImportResult(
        "second",
        ScreenType.SQUAD_ATTRIBUTES,
        [ExtractedPlayer("Max Power", "DM", "114", "130", {"passing": 12}, 0.97)],
    )

    merged = squadCapturesMerge(first, second)

    assert merged.players[0].attributes["passing"] == 15
    assert merged.mergeConflicts == ["Max Power: passing 15 / 12"]


def testSquadCaptureMergeAccumulatesEverySourceImage() -> None:

    player = ExtractedPlayer("Max Power", "DM", "114", "130", {}, 0.98)
    captures = [
        ImportResult(
            f"capture-{index}",
            ScreenType.SQUAD_ATTRIBUTES,
            [player],
            image=np.full((2, 2, 3), index, dtype=np.uint8),
        )
        for index in range(3)
    ]

    merged = squadCapturesMerge(squadCapturesMerge(captures[0], captures[1]), captures[2])

    assert merged.image is not None
    assert len(merged.additionalImages) == 2
