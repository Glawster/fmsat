"""Configuration-driven tactic screen parser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..ocr import OcrEngine
from ..textCleanup import ocrTextClean
from .squadAttributes import ParserError


@dataclass(frozen=True, slots=True)
class ExtractedTactic:
    """A tactic name extracted from a screenshot."""

    name: str
    confidence: float


class TacticParser:
    """Extract a tactic name from a configured normalized screen region."""

    def __init__(self, ocr: OcrEngine, regions: dict[str, Any]) -> None:
        self.ocr = ocr
        self.regions = regions

    def parse(self, image: np.ndarray) -> ExtractedTactic:
        """Return the text found in the configured tactic-name region."""

        settings = self.regions.get("tactic")
        if not isinstance(settings, dict) or not isinstance(settings.get("name"), dict):
            raise ParserError("Missing tactic name region configuration")
        crop = self._regionCrop(image, settings["name"])
        results = self.ocr.recognize(crop)
        text = ocrTextClean(
            " ".join(result.text.strip() for result in results if result.text.strip())
        )
        if not text:
            raise ParserError("No tactic name could be extracted from the screenshot")
        confidence = sum(result.confidence for result in results) / len(results)
        return ExtractedTactic(text, confidence)

    @staticmethod
    def _regionCrop(image: np.ndarray, region: dict[str, float]) -> np.ndarray:
        height, width = image.shape[:2]
        left = int(round(float(region["x"]) * width))
        top = int(round(float(region["y"]) * height))
        right = min(width, left + int(round(float(region["width"]) * width)))
        bottom = min(height, top + int(round(float(region["height"]) * height)))
        if right <= left or bottom <= top:
            raise ParserError("Configured tactic name region is empty")
        return image[top:bottom, left:right]
