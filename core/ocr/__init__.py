"""Replaceable OCR adapters."""

from .base import OcrEngine, OcrResult
from .paddle import PaddleOcrEngine

__all__ = ["OcrEngine", "OcrResult", "PaddleOcrEngine"]
