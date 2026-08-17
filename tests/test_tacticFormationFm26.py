"""Regression coverage for FM26 formation geometry and role OCR refinement."""

import cv2
import numpy as np

from fmsat.core.ocr import OcrResult
from fmsat.core.parser import TacticalPhase, TacticFormationExtractor, TacticVocabulary
from fmsat.tests.conftest import FakeOcr


def testFormationPitchDepthUsesVisibleFieldInsteadOfConfiguredShortCrop() -> None:
    """A wide Planner capture must retain the defensive and goalkeeper rows."""

    image = np.zeros((832, 2048, 3), dtype=np.uint8)
    pitchColour = (58, 67, 12)
    cv2.rectangle(image, (49, 163), (603, 819), pitchColour, -1)
    cv2.rectangle(image, (649, 163), (1203, 819), pitchColour, -1)
    configured = {
        "inPossession": {"x": 0.024, "y": 0.218, "width": 0.271, "height": 0.550},
        "outOfPossession": {"x": 0.317, "y": 0.218, "width": 0.271, "height": 0.550},
    }
    extractor = TacticFormationExtractor(
        FakeOcr([]),
        TacticVocabulary(),
        {"phaseRegions": configured},
    )

    regions = extractor._phaseRegionsResolve(image)

    for phase in ("inPossession", "outOfPossession"):
        assert regions[phase]["y"] == configured[phase]["y"]
        assert regions[phase]["height"] > 0.75
        assert regions[phase]["y"] + regions[phase]["height"] > 0.98
        assert regions[phase]["x"] == configured[phase]["x"]
        assert regions[phase]["width"] == configured[phase]["width"]


def testFormationPitchDepthFallsBackWhenVisibleFieldCannotBeEstablished() -> None:
    configured = {
        "inPossession": {"x": 0.024, "y": 0.218, "width": 0.271, "height": 0.550},
        "outOfPossession": {"x": 0.317, "y": 0.218, "width": 0.271, "height": 0.550},
    }
    extractor = TacticFormationExtractor(
        FakeOcr([]),
        TacticVocabulary(),
        {"phaseRegions": configured},
    )

    regions = extractor._phaseRegionsResolve(np.zeros((832, 2048, 3), dtype=np.uint8))

    assert regions == configured


def testFocusedRoleLabelOcrRecoversAbbreviationMissedByExpandedCrop(monkeypatch) -> None:
    """A clean role-label retry should win when the larger player-card crop returns junk."""

    pitch = np.full((200, 300, 3), 40, dtype=np.uint8)
    ocr = FakeOcr([
        [OcrResult("B", 0.75)],
        [OcrResult("BGK", 0.99)],
    ])
    extractor = TacticFormationExtractor(
        ocr,
        TacticVocabulary(),
        {
            "pitchZones": {
                "bands": [
                    {
                        "yMin": 0.0,
                        "yMax": 1.01,
                        "positions": [
                            {"xMin": 0.0, "xMax": 1.01, "code": "GK"},
                        ],
                    }
                ]
            }
        },
    )
    monkeypatch.setattr(extractor, "_tilesDetect", lambda _pitch: [(100, 80, 180, 105)])

    slots, issues = extractor._phaseExtract(
        pitch,
        TacticalPhase.IN_POSSESSION,
        "formation.png",
    )

    assert len(slots) == 1
    assert slots[0].role == "ballPlayingGoalkeeper"
    assert slots[0].observedRole == "BGK"
    assert not [issue for issue in issues if issue.code == "unresolvedRole"]


def testHorizontalRoleBarRecoveryFindsLabelAndRejectsCircularIcon() -> None:
    pitch = np.full((300, 300, 3), (58, 67, 12), dtype=np.uint8)
    cv2.rectangle(pitch, (180, 120), (265, 138), (170, 45, 20), -1)
    cv2.circle(pitch, (150, 130), 12, (170, 45, 20), -1)
    extractor = TacticFormationExtractor(
        FakeOcr([]),
        TacticVocabulary(),
        {"tileDetection": {"excludedRegions": []}},
    )

    boxes = extractor._horizontalRoleBarsDetect(pitch)

    assert any(left <= 180 and right >= 265 for left, _, right, _ in boxes)
    assert not any(left <= 150 <= right and right - left < 60 for left, _, right, _ in boxes)


def testGoalkeeperRecoveryAcceptsLowerCentreTallerLabel() -> None:
    pitch = np.full((300, 300, 3), (58, 67, 12), dtype=np.uint8)
    cv2.rectangle(pitch, (100, 250), (200, 278), (100, 65, 120), -1)
    extractor = TacticFormationExtractor(
        FakeOcr([]),
        TacticVocabulary(),
        {"tileDetection": {"excludedRegions": []}},
    )

    boxes = extractor._goalkeeperRoleBoxDetect(pitch)

    assert boxes


def testFormationRejectsCandidateWithoutRoleLabelText(monkeypatch) -> None:
    """Geometry alone is not enough evidence that a detected rectangle is a role tile."""

    pitch = np.full((200, 300, 3), 40, dtype=np.uint8)
    ocr = FakeOcr([
        [OcrResult("Player Name", 0.95)],
        [],
    ])
    extractor = TacticFormationExtractor(
        ocr,
        TacticVocabulary(),
        {"pitchZones": {"bands": []}},
    )
    monkeypatch.setattr(extractor, "_tilesDetect", lambda _pitch: [(100, 80, 180, 105)])

    slots, issues = extractor._phaseExtract(
        pitch,
        TacticalPhase.IN_POSSESSION,
        "formation.png",
    )

    assert slots == []
    assert any(issue.code == "missingFormationSlots" for issue in issues)
