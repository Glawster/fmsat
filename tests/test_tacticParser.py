import numpy as np
import pytest

from fmsat.core.config import Configuration
from fmsat.core.ocr import OcrResult
from fmsat.core.parser import TacticParser
from fmsat.core.parser.squadAttributes import ParserError
from fmsat.tests.conftest import FakeOcr


def testTacticNameIsReadFromConfiguredRegion() -> None:

    parser = TacticParser(
        FakeOcr([[OcrResult(" .- 3-3-3-1", 0.98), OcrResult("High Press", 0.96)]]),
        {"tactic": {"name": {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.1}}},
    )

    tactic = parser.parse(np.zeros((100, 200, 3), dtype=np.uint8))

    assert tactic.name == "3-3-3-1 High Press"
    assert tactic.confidence == pytest.approx(0.97)


def testEmptyTacticNameIsRejected() -> None:

    parser = TacticParser(
        FakeOcr([[]]),
        {"tactic": {"name": {"x": 0, "y": 0, "width": 1, "height": 1}}},
    )

    with pytest.raises(ParserError, match="No tactic name"):
        parser.parse(np.zeros((100, 100, 3), dtype=np.uint8))


def testConfiguredTacticNameRegionCropsThePlannerSelector() -> None:

    image = np.zeros((1004, 2048, 3), dtype=np.uint8)
    region = Configuration().regions["tactic"]["name"]

    crop = TacticParser._regionCrop(image, region)

    assert crop.shape == (55, 512, 3)
