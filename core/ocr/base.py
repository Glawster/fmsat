"""OCR contracts used by detection and parsing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class OcrResult:
    """One recognized text fragment."""

    text: str
    confidence: float
    bounds: tuple[float, float, float, float] | None = None

    @property
    def center(self) -> tuple[float, float] | None:
        """Return the centre of the OCR box when positional data is available."""

        if self.bounds is None:
            return None
        left, top, right, bottom = self.bounds
        return ((left + right) / 2, (top + bottom) / 2)


class OcrEngine(ABC):
    """Replaceable OCR engine interface."""

    @abstractmethod
    def recognize(self, image: np.ndarray) -> list[OcrResult]:
        """Recognize text fragments in reading order."""

    @property
    def suppliesGeometry(self) -> bool:
        """Return whether recognition results contain image-relative boxes."""

        return False
