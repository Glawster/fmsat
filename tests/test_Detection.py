"""Screen detector tests."""

from unittest.mock import Mock

import numpy as np

from fmsat.core.detection import KeywordScreenDetector, ScreenType
from fmsat.core.ocr import OcrResult
from fmsat.tests.conftest import FakeOcr


def testDetectsSquadAttributesFromConfiguredKeywords() -> None:

    detector = KeywordScreenDetector(
        FakeOcr([[OcrResult("Squad Attributes", 0.99), OcrResult("Name", 0.98)]]),
        ["Squad", "Attributes", "Name", "Position"],
    )

    assert detector.detect(np.zeros((100, 100, 3), dtype=np.uint8)) is ScreenType.SQUAD_ATTRIBUTES


def testDetectsCroppedSquadTableFromStableColumnHeaders() -> None:

    detector = KeywordScreenDetector(
        FakeOcr([[OcrResult("Position CA PA", 0.99)]]),
        ["Squad", "Attributes", "Name", "Position", "CA", "PA"],
    )

    assert detector.detect(np.zeros((100, 100, 3), dtype=np.uint8)) is ScreenType.SQUAD_ATTRIBUTES


def testUnknownWhenKeywordEvidenceIsInsufficient() -> None:

    detector = KeywordScreenDetector(
        FakeOcr([[OcrResult("Tactics", 0.99)]]),
        ["Squad", "Attributes", "Name", "Position"],
    )

    assert detector.detect(np.zeros((100, 100, 3), dtype=np.uint8)) is ScreenType.UNKNOWN


def testDetectionAreaIncludesTheFirstTeamInstructionsRow() -> None:

    ocr = Mock()
    ocr.recognize.return_value = []
    detector = KeywordScreenDetector(ocr, ["Squad", "Attributes", "Name", "Position"])

    detector.detect(np.zeros((1000, 1600, 3), dtype=np.uint8))

    assert ocr.recognize.call_args.args[0].shape == (450, 1600, 3)


def testDetectsConfiguredTacticScreenTypes() -> None:

    detector = KeywordScreenDetector(
        FakeOcr([[OcrResult("Tactics In Possession Passing", 0.99)]]),
        {
            ScreenType.TACTIC_FORMATION: ["Formation", "Mentality", "Familiarity"],
            ScreenType.TACTIC_IN_POSSESSION: ["In", "Possession", "Passing"],
            ScreenType.TACTIC_OUT_OF_POSSESSION: ["Out", "Possession", "Press"],
        },
    )

    assert detector.detect(np.zeros((100, 100, 3), dtype=np.uint8)) is (
        ScreenType.TACTIC_IN_POSSESSION
    )


def testTacticsPlannerBothViewIsDetectedAsFormation() -> None:

    detector = KeywordScreenDetector(
        FakeOcr(
            [
                [
                    OcrResult(
                        "Squad Tactics Planner Team Shape Combined In Possession "
                        "Out of Possession Both High Press Mentality Familiarity",
                        0.99,
                    )
                ]
            ]
        ),
        {
            ScreenType.TACTIC_FORMATION: ["Planner", "Shape", "Combined", "Both"],
            ScreenType.TACTIC_IN_POSSESSION: ["In", "Possession", "Passing"],
            ScreenType.TACTIC_OUT_OF_POSSESSION: ["Out", "Possession", "Press"],
        },
    )

    assert detector.detect(np.zeros((100, 100, 3), dtype=np.uint8)) is (ScreenType.TACTIC_FORMATION)


def testTacticsPlannerFormationWinsWhenOcrMissesSomeOverviewLabels() -> None:

    detector = KeywordScreenDetector(
        FakeOcr(
            [
                [
                    OcrResult(
                        "Tactics Planner Team Shape Out of Possession High Press",
                        0.99,
                    )
                ]
            ]
        ),
        {
            ScreenType.TACTIC_FORMATION: ["Planner", "Shape", "Combined", "Both"],
            ScreenType.TACTIC_IN_POSSESSION: ["In", "Possession", "Passing"],
            ScreenType.TACTIC_OUT_OF_POSSESSION: ["Out", "Possession", "Press"],
        },
    )

    assert detector.detect(np.zeros((100, 100, 3), dtype=np.uint8)) is (ScreenType.TACTIC_FORMATION)


def testInPossessionInstructionsOverrideDimmedPlannerBackground() -> None:

    detector = KeywordScreenDetector(
        FakeOcr(
            [
                [
                    OcrResult(
                        "Tactics Planner Team Shape Team Instructions In Possession "
                        "Passing Directness Attacking Width",
                        0.99,
                    )
                ]
            ]
        ),
        {
            ScreenType.TACTIC_FORMATION: ["Planner", "Shape", "Combined", "Both"],
            ScreenType.TACTIC_IN_POSSESSION: [
                "In",
                "Possession",
                "Attacking",
                "Width",
                "Passing",
            ],
            ScreenType.TACTIC_OUT_OF_POSSESSION: [
                "Out",
                "Possession",
                "Defensive",
                "Line",
                "Press",
            ],
        },
    )

    assert detector.detect(np.zeros((100, 100, 3), dtype=np.uint8)) is (
        ScreenType.TACTIC_IN_POSSESSION
    )


def testOutOfPossessionInstructionsOverrideDimmedInPossessionBackground() -> None:

    detector = KeywordScreenDetector(
        FakeOcr(
            [
                [
                    OcrResult(
                        "Tactics Planner Team Shape In Possession Passing Directness "
                        "Attacking Width Out of Possession Line of Engagement "
                        "Defensive Line Trigger Press Defensive Transition",
                        0.99,
                    )
                ]
            ]
        ),
        {
            ScreenType.TACTIC_FORMATION: ["Planner", "Shape", "Combined", "Both"],
            ScreenType.TACTIC_IN_POSSESSION: [
                "In",
                "Possession",
                "Attacking",
                "Width",
                "Passing",
            ],
            ScreenType.TACTIC_OUT_OF_POSSESSION: [
                "Out",
                "Possession",
                "Defensive",
                "Line",
                "Press",
            ],
        },
    )

    assert detector.detect(np.zeros((100, 100, 3), dtype=np.uint8)) is (
        ScreenType.TACTIC_OUT_OF_POSSESSION
    )
