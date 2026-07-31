"""Screen type detection contracts and Phase 1 implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

import numpy as np

from .ocr import OcrEngine


class ScreenType(str, Enum):  # noqa: UP042 - keeps local Python 3.10 verification possible
    """Known Football Manager screenshot types."""

    UNKNOWN = "UNKNOWN"
    SQUAD_ATTRIBUTES = "SQUAD_ATTRIBUTES"


class ScreenDetector(ABC):
    """Abstract screen detector for future screen-specific implementations."""

    @abstractmethod
    def detect(self, image: np.ndarray) -> ScreenType:
        """Return the recognized screen type."""


class KeywordScreenDetector(ScreenDetector):
    """Detects the Squad Attributes screen from configured header keywords."""

    def __init__(
        self,
        ocr: OcrEngine,
        keywords: list[str],
        minimumConfidence: float = 0.55,
    ) -> None:
        self.ocr = ocr
        self.keywords = {word.casefold() for word in keywords}
        self.minimumConfidence = minimumConfidence

    def detect(self, image: np.ndarray) -> ScreenType:
        """OCR the top area and score configured keyword matches."""

        header = image[: max(1, int(image.shape[0] * 0.3)), :]
        recognized = {
            token.casefold()
            for result in self.ocr.recognize(header)
            if result.confidence >= self.minimumConfidence
            for token in result.text.split()
        }
        requiredMatches = max(2, len(self.keywords) // 2)
        if len(self.keywords & recognized) >= requiredMatches:
            return ScreenType.SQUAD_ATTRIBUTES
        return ScreenType.UNKNOWN
