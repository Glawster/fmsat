"""OCR adapter tests."""

from unittest.mock import Mock

import numpy as np

from fmsat.core.ocr import PaddleOcrEngine


def testPaddleAdapterPreservesRecognizedTextBounds() -> None:
    engine = Mock()
    engine.ocr.return_value = [
        [
            [
                [[10, 20], [50, 20], [50, 32], [10, 32]],
                ("Position", 0.98),
            ]
        ]
    ]
    ocr = PaddleOcrEngine(engine=engine)

    results = ocr.recognize(np.zeros((100, 100, 3), dtype=np.uint8))

    assert ocr.suppliesGeometry
    assert results[0].text == "Position"
    assert results[0].bounds == (10.0, 20.0, 50.0, 32.0)
    assert results[0].center == (30.0, 26.0)
