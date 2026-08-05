"""PaddleOCR adapter with lazy model initialization."""

from __future__ import annotations

import threading
from typing import Any

import numpy as np

from .base import OcrEngine, OcrResult


class OcrError(RuntimeError):
    """Raised when OCR cannot be initialized or completed."""


class PaddleOcrEngine(OcrEngine):
    """Adapts PaddleOCR to the small engine-neutral OCR contract."""

    def __init__(self, language: str = "en", engine: Any | None = None) -> None:
        self.language = language
        self._engine = engine
        self._lock = threading.Lock()

    def recognize(self, image: np.ndarray) -> list[OcrResult]:
        """Recognize an image and normalize version-dependent Paddle output."""

        try:
            raw = self._engineGet().ocr(image, cls=False)
        except Exception as exc:
            raise OcrError(f"OCR failed: {exc}") from exc
        results: list[OcrResult] = []
        for page in raw or []:
            for line in page or []:
                if len(line) >= 2 and isinstance(line[1], (tuple, list)):
                    text, confidence = line[1][:2]
                    bounds = self._boundsRead(line[0])
                    results.append(OcrResult(str(text).strip(), float(confidence), bounds))
        return [result for result in results if result.text]

    @property
    def suppliesGeometry(self) -> bool:
        """PaddleOCR supplies a quadrilateral for every recognized fragment."""

        return True

    @staticmethod
    def _boundsRead(value: Any) -> tuple[float, float, float, float] | None:
        try:
            points = [(float(point[0]), float(point[1])) for point in value]
        except (TypeError, ValueError, IndexError):
            return None
        if not points:
            return None
        horizontal = [point[0] for point in points]
        vertical = [point[1] for point in points]
        return min(horizontal), min(vertical), max(horizontal), max(vertical)

    def _engineGet(self) -> Any:
        if self._engine is not None:
            return self._engine
        with self._lock:
            if self._engine is None:
                try:
                    from paddleocr import PaddleOCR
                except ImportError as exc:
                    raise OcrError(
                        "PaddleOCR is not installed. Install the project dependencies first."
                    ) from exc
                self._engine = PaddleOCR(use_angle_cls=False, lang=self.language, show_log=False)
        return self._engine
