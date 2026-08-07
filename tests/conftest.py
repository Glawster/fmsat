"""Shared test doubles."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from fmsat.core.ocr import OcrEngine, OcrResult


class FakeOcr(OcrEngine):
    """Returns configured OCR batches in call order."""

    def __init__(
        self,
        batches: Iterable[list[OcrResult]],
        *,
        suppliesGeometry: bool = False,
    ) -> None:
        self.batches = iter(batches)
        self._suppliesGeometry = suppliesGeometry

    def ocrRecognize(self, image: np.ndarray) -> list[OcrResult]:
        del image
        return next(self.batches, [])

    recognize = ocrRecognize

    @property
    def suppliesGeometry(self) -> bool:
        return self._suppliesGeometry
