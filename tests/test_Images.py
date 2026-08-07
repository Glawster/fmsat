"""Image preprocessing tests."""

import numpy as np
import pytest

pytest.importorskip("cv2")

from fmsat.core.images import ImagePreprocessor, PreprocessingOptions


def testProcessKeepsThreeChannelsAndCropsBorder() -> None:

    image = np.zeros((100, 200, 3), dtype=np.uint8)
    options = PreprocessingOptions(
        cropBorders=True,
        borderFraction=0.1,
        increaseContrast=False,
        denoise=False,
        sharpen=False,
    )

    processed = ImagePreprocessor(options).process(image)

    assert processed.shape == (80, 160, 3)


def testEmptyImageIsRejected() -> None:

    with pytest.raises(RuntimeError, match="empty image"):
        ImagePreprocessor().process(np.array([], dtype=np.uint8))
