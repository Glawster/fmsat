"""Golden regressions which run the real OCR formation extractor."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import cv2
import pytest
import yaml

from fmsat.core.config import Configuration
from fmsat.core.ocr import PaddleOcrEngine
from fmsat.core.parser import TacticFormationExtractor, TacticVocabulary, TacticalPhase


_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "tactics"
_FORMATION_FIXTURES = ("highPress", "highPress2", "libero1974", "liberoWealdstone")


@pytest.fixture(scope="module")
def ocrEngine() -> PaddleOcrEngine:
    """Reuse one real PaddleOCR model across the formation golden tests."""

    return PaddleOcrEngine()


def _fixtureLoad(name: str) -> dict:
    return yaml.safe_load((_FIXTURE_ROOT / f"{name}.yaml").read_text(encoding="utf-8"))


def _slotRoleLabel(slot, vocabulary: TacticVocabulary) -> str:  # type: ignore[no-untyped-def]
    """Return the exact reviewed role label represented by one extracted slot."""

    if slot.role:
        role = vocabulary.roles.get(slot.role)
        if role is not None and role.abbreviations:
            return role.abbreviations[0]
    return str(slot.observedRole or "")


def _formationExtract(fixtureName: str, ocrEngine: PaddleOcrEngine):  # type: ignore[no-untyped-def]
    fixture = _fixtureLoad(fixtureName)
    imagePath = Path(fixture["screenshots"]["formation"])
    image = cv2.imread(str(imagePath))
    assert image is not None, f"Unable to read {imagePath}"

    configuration = Configuration()
    vocabulary = TacticVocabulary()
    result = TacticFormationExtractor(
        ocrEngine,
        vocabulary,
        configuration.tacticExtraction,
    ).formationExtract(image, str(imagePath))
    return fixture, vocabulary, result


def _phaseSlots(result, phase: TacticalPhase):  # type: ignore[no-untyped-def]
    return tuple(slot for slot in result.slots if slot.phase is phase)


@pytest.mark.parametrize("fixtureName", _FORMATION_FIXTURES)
def testFormationScreenshotRunsRealOcrAndPreservesReviewedRoles(
    fixtureName: str,
    ocrEngine: PaddleOcrEngine,
) -> None:
    """Real OCR drift must fail against the reviewed canonical formation screenshots."""

    fixture, vocabulary, result = _formationExtract(fixtureName, ocrEngine)
    expected = fixture["expected"]
    inPossession = _phaseSlots(result, TacticalPhase.IN_POSSESSION)
    outOfPossession = _phaseSlots(result, TacticalPhase.OUT_OF_POSSESSION)

    assert len(inPossession) == 11
    assert len(outOfPossession) == 11
    # Detection order follows the observed y/x geometry and can legitimately
    # differ where two role bars are only a few pixels apart. OCR identity is
    # golden evidence, so compare the complete role multiset rather than hiding
    # a real OCR miss behind a synthetic ordering contract.
    assert Counter(_slotRoleLabel(slot, vocabulary) for slot in inPossession) == Counter(
        expected["inPossessionRoles"]
    )
    assert Counter(_slotRoleLabel(slot, vocabulary) for slot in outOfPossession) == Counter(
        expected["outOfPossessionRoles"]
    )


def testLiberoWealdstoneRealOcrPreservesReviewedPitchPositions(
    ocrEngine: PaddleOcrEngine,
) -> None:
    """The reviewed Libero role/position combinations must not drift between bands."""

    fixture, vocabulary, result = _formationExtract("liberoWealdstone", ocrEngine)
    expected = fixture["expected"]
    inPossession = _phaseSlots(result, TacticalPhase.IN_POSSESSION)
    outOfPossession = _phaseSlots(result, TacticalPhase.OUT_OF_POSSESSION)

    expectedIn = Counter(zip(expected["inPossessionRoles"], expected["inPossessionPositions"]))
    expectedOut = Counter(zip(expected["outOfPossessionRoles"], expected["outOfPossessionPositions"]))
    actualIn = Counter(
        (_slotRoleLabel(slot, vocabulary), slot.position) for slot in inPossession
    )
    actualOut = Counter(
        (_slotRoleLabel(slot, vocabulary), slot.position) for slot in outOfPossession
    )

    assert actualIn == expectedIn
    assert actualOut == expectedOut


def testLiberoCentreForwardIsCloserToGoalThanTrackingCentreForward(
    ocrEngine: PaddleOcrEngine,
) -> None:
    """Retain the small FM pitch-depth difference visible between CFD and TCF."""

    _fixture, vocabulary, result = _formationExtract("liberoWealdstone", ocrEngine)
    cfd = next(
        slot
        for slot in result.slots
        if slot.phase is TacticalPhase.IN_POSSESSION
        and _slotRoleLabel(slot, vocabulary) == "CFD"
    )
    tcf = next(
        slot
        for slot in result.slots
        if slot.phase is TacticalPhase.OUT_OF_POSSESSION
        and _slotRoleLabel(slot, vocabulary) == "TCF"
    )

    assert cfd.y < tcf.y
