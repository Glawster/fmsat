"""Tests for evidence-only Formation pitch extraction and phase linking."""

from __future__ import annotations

import cv2
import numpy as np

from fmsat.core.ocr import OcrResult
from fmsat.core.parser import (
    FormationPhaseLinker,
    FormationSlot,
    PitchZoneClassifier,
    TacticalPhase,
    TacticFormationExtractor,
    TacticVocabulary,
)
from fmsat.tests.conftest import FakeOcr


def _zones():
    return {"bands": [
        {"yMin": 0.0, "yMax": 0.5, "positions": [
            {"xMin": 0.0, "xMax": 1.01, "code": "STC"},
        ]},
        {"yMin": 0.5, "yMax": 1.01, "positions": [
            {"xMin": 0.0, "xMax": 1.01, "code": "GK"},
        ]},
    ]}


def testPitchZonesClassifyBoundariesFromConfiguration() -> None:
    classifier = PitchZoneClassifier(_zones())

    assert classifier.positionClassify(0.5, 0.49) == "STC"
    assert classifier.positionClassify(0.5, 0.50) == "GK"
    assert classifier.positionClassify(1.2, 0.50) is None


def testFormationExtractorDetectsTilesBeforeFocusedOcr() -> None:
    image = np.full((200, 400, 3), 35, dtype=np.uint8)
    cv2.rectangle(image, (40, 20), (150, 55), (180, 20, 180), -1)
    cv2.rectangle(image, (240, 110), (350, 145), (180, 20, 180), -1)
    ocr = FakeOcr([
        [OcrResult("Alex Forward", 0.96), OcrResult("CFD", 0.98), OcrResult("Attack", 0.97)],
        [OcrResult("Alex Forward", 0.95), OcrResult("CFD", 0.97), OcrResult("Support", 0.96)],
    ])
    configuration = {
        "phaseRegions": {
            "inPossession": {"x": 0.0, "y": 0.0, "width": 0.5, "height": 1.0},
            "outOfPossession": {"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0},
        },
        "tileDetection": {
            "cannyLow": 20,
            "cannyHigh": 80,
            "minimumWidth": 0.2,
            "maximumWidth": 0.8,
            "minimumHeight": 0.05,
            "maximumHeight": 0.3,
        },
        "pitchZones": _zones(),
    }

    result = TacticFormationExtractor(
        ocr, TacticVocabulary(), configuration
    ).formationExtract(image, "formation.png")

    assert len(result.slots) == 2
    assert {slot.phase for slot in result.slots} == {
        TacticalPhase.IN_POSSESSION,
        TacticalPhase.OUT_OF_POSSESSION,
    }
    assert {slot.slotId for slot in result.slots} == {"slot-01"}
    assert result.slots[0].role == "centreForward"
    assert result.slots[0].displayedPlayer == "Alex Forward"
    assert not result.issues
    assert result.diagnosticImage is not None
    assert result.diagnosticImage.shape == image.shape


def testFormationTileDetectionCollapsesElementsFromOnePlayerCard() -> None:
    boxes = [
        (100, 100, 170, 118),
        (112, 122, 157, 145),
        (260, 100, 330, 118),
    ]

    retained = TacticFormationExtractor._duplicatesRemove(boxes, 400, 400)

    assert len(retained) == 2


def testFormationTileDetectionExcludesPitchControlAndPhaseBadge() -> None:
    extractor = TacticFormationExtractor(
        FakeOcr([]),
        TacticVocabulary(),
        {"tileDetection": {"excludedRegions": [
            {"x": 0.0, "y": 0.0, "width": 0.2, "height": 0.1},
            {"x": 0.0, "y": 0.9, "width": 0.25, "height": 0.1},
        ]}},
    )

    assert extractor._excludedCandidate((5, 5, 45, 25), 400, 400) is True
    assert extractor._excludedCandidate((5, 365, 90, 390), 400, 400) is True
    assert extractor._excludedCandidate((150, 5, 250, 30), 400, 400) is False


def testPhaseLinkerRetainsUnmatchedSlotsAndReportsIssue() -> None:
    source = FormationSlot(
        "ip", TacticalPhase.IN_POSSESSION, "STC", "centreForward", "ATTACK", 0.5, 0.1
    )
    target = FormationSlot(
        "oop", TacticalPhase.OUT_OF_POSSESSION, "GK", "sweeperKeeper", "DEFEND", 0.5, 0.95
    )

    linkedIn, linkedOut, issues = FormationPhaseLinker(maximumDistance=0.1).phasesLink(
        [source], [target]
    )

    assert linkedIn[0].slotId == "slot-01"
    assert linkedOut[0].slotId == "slot-02"
    assert {issue.code for issue in issues} == {"uncertainPhaseLink", "unmatchedPhaseSlot"}
