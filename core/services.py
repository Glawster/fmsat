"""Application services coordinating core components."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .detection import ScreenDetector, ScreenType
from .images import ImagePreprocessor, imageLoad
from .parser import ExtractedPlayer, SquadAttributesParser

logger = logging.getLogger(__name__)


class ImportError(RuntimeError):
    """Raised when a screenshot import cannot reach the review stage."""


@dataclass(slots=True)
class ImportResult:
    """Reviewable result returned to the UI."""

    source: str
    screenType: ScreenType
    players: list[ExtractedPlayer]


class ScreenshotImportService:
    """Coordinates loading, preprocessing, detection, and screen parsing."""

    def __init__(
        self,
        preprocessor: ImagePreprocessor,
        detector: ScreenDetector,
        parser: SquadAttributesParser,
    ) -> None:
        self.preprocessor = preprocessor
        self.detector = detector
        self.parser = parser

    def fileImport(self, path: Path) -> ImportResult:
        """Import a supported screenshot from disk."""

        return self.imageImport(imageLoad(path), str(path))

    def imageImport(self, image: np.ndarray, source: str = "clipboard") -> ImportResult:
        """Import a decoded screenshot from any source."""

        started = time.perf_counter()
        try:
            processed = self.preprocessor.process(image)
            screenType = self.detector.detect(processed)
            logger.info("Detected screen type %s for %s", screenType.value, source)
            if screenType is not ScreenType.SQUAD_ATTRIBUTES:
                raise ImportError("The screenshot is not a supported Squad Attributes screen")
            players = self.parser.parse(processed)
            if not players:
                raise ImportError("No player rows could be extracted from the screenshot")
            return ImportResult(source, screenType, players)
        except ImportError:
            raise
        except Exception as exc:
            logger.exception("Screenshot import failed for %s", source)
            raise ImportError(f"Unable to import screenshot: {exc}") from exc
        finally:
            logger.info(
                "OCR import duration %.3f seconds for %s",
                time.perf_counter() - started,
                source,
            )
