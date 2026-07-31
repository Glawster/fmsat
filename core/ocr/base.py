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


class OcrEngine(ABC):
    """Replaceable OCR engine interface."""

    @abstractmethod
    def recognize(self, image: np.ndarray) -> list[OcrResult]:
        """Recognize text fragments in reading order."""
