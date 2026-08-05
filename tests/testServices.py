"""Screenshot import service tests."""

from unittest.mock import Mock

import numpy as np

from fmsat.core.detection import ScreenType
from fmsat.core.services import ScreenshotImportService


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
