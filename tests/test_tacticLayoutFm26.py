"""Regression coverage for FM26 tactic layout refinements."""

import cv2
import numpy as np

from fmsat.core.parser import TacticalPhase, TacticLayoutAnchor
from fmsat.tests.conftest import FakeOcr


def _configuration() -> dict:
    return {
        "anchors": {
            "enabled": True,
            "tabBandYMin": 0.08,
            "tabBandYMax": 0.24,
            "instructionTabSplit": 0.18,
            "underlineBrightness": 170,
        }
    }


def _segmentedLine(image: np.ndarray, start: int, end: int, y: int) -> None:
    for left in range(start, end, 30):
        cv2.line(
            image,
            (left, y),
            (min(left + 24, end), y),
            (215, 215, 215),
            2,
        )


def testThinSegmentedInPossessionUnderlineIsRecovered() -> None:
    panel = np.full((895, 1505, 3), 20, dtype=np.uint8)
    _segmentedLine(panel, 20, 210, 153)
    anchor = TacticLayoutAnchor(FakeOcr([]), _configuration())

    assert anchor._activePhaseDetect(panel) is TacticalPhase.IN_POSSESSION


def testThinSegmentedOutOfPossessionUnderlineIsRecovered() -> None:
    panel = np.full((652, 1505, 3), 20, dtype=np.uint8)
    _segmentedLine(panel, 190, 430, 130)
    anchor = TacticLayoutAnchor(FakeOcr([]), _configuration())

    assert anchor._activePhaseDetect(panel) is TacticalPhase.OUT_OF_POSSESSION
