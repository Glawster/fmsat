"""Regression coverage for FM26 goalkeeper role-position recovery."""

from fmsat.core.ocr import OcrResult
from fmsat.core.parser import TacticalPhase, TacticFormationExtractor, TacticVocabulary
from fmsat.tests.conftest import FakeOcr


def _extractor() -> TacticFormationExtractor:
    return TacticFormationExtractor(
        FakeOcr([]),
        TacticVocabulary(),
        {
            "pitchZones": {
                "bands": [
                    {
                        "yMin": 0.0,
                        "yMax": 1.01,
                        "positions": [
                            {"xMin": 0.0, "xMax": 1.01, "code": "DC"},
                        ],
                    }
                ]
            }
        },
    )


def testGoalkeeperRoleEvidenceRecoversGkPositionNearDcBoundary() -> None:
    extractor = _extractor()

    slot, _issues = extractor._slotBuild(
        [OcrResult("BGK", 0.99)],
        TacticalPhase.IN_POSSESSION,
        0.50,
        0.83,
        "formation.png",
        1,
    )

    assert slot.role == "ballPlayingGoalkeeper"
    assert slot.position == "GK"


def testSweeperKeeperRoleEvidenceRecoversGkPositionNearDcBoundary() -> None:
    extractor = _extractor()

    slot, _issues = extractor._slotBuild(
        [OcrResult("SK", 0.99)],
        TacticalPhase.OUT_OF_POSSESSION,
        0.50,
        0.83,
        "formation.png",
        1,
    )

    assert slot.role == "sweeperKeeper"
    assert slot.position == "GK"


def testCentreBackRoleRemainsDcAtSameDepth() -> None:
    extractor = _extractor()

    slot, _issues = extractor._slotBuild(
        [OcrResult("CB", 0.99)],
        TacticalPhase.IN_POSSESSION,
        0.50,
        0.83,
        "formation.png",
        1,
    )

    assert slot.role == "centreBack"
    assert slot.position == "DC"
