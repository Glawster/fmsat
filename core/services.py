"""Application services coordinating core components."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .detection import ScreenDetector, ScreenType
from .images import ImagePreprocessor, imageLoad
from .parser import ExtractedPlayer, SquadAttributesParser, TacticParser

logger = logging.getLogger(__name__)


class ImportError(RuntimeError):
    """Raised when a screenshot import cannot reach the review stage."""


@dataclass(slots=True)
class ImportResult:
    """Reviewable result returned to the UI."""

    source: str
    screenType: ScreenType
    players: list[ExtractedPlayer]
    tacticName: str | None = None
    confidence: float = 0.0


class ScreenshotImportService:
    """Coordinates loading, preprocessing, detection, and screen parsing."""

    def __init__(
        self,
        preprocessor: ImagePreprocessor,
        detector: ScreenDetector,
        squadParser: SquadAttributesParser,
        tacticParser: TacticParser,
    ) -> None:
        self.preprocessor = preprocessor
        self.detector = detector
        self.squadParser = squadParser
        self.tacticParser = tacticParser

    def fileImport(self, path: Path, expectedType: ScreenType) -> ImportResult:
        """Import a supported screenshot from disk."""

        return self.imageImport(imageLoad(path), expectedType, str(path))

    def imageImport(
        self,
        image: np.ndarray,
        expectedType: ScreenType,
        source: str = "clipboard",
    ) -> ImportResult:
        """Import a decoded screenshot from any source."""

        started = time.perf_counter()
        try:
            processed = self.preprocessor.process(image)
            screenType = self.detector.detect(processed)
            logger.info("Detected screen type %s for %s", screenType.value, source)
            if screenType is not expectedType:
                instructionTypes = {
                    ScreenType.TACTIC_IN_POSSESSION,
                    ScreenType.TACTIC_OUT_OF_POSSESSION,
                }
                if {screenType, expectedType}.issubset(instructionTypes):
                    logger.warning(
                        "Instruction screen detection was ambiguous (%s); using requested type %s",
                        screenType.value,
                        expectedType.value,
                    )
                    screenType = expectedType
                else:
                    raise ImportError(
                        f"Expected a {expectedType.value} screenshot but detected "
                        f"{screenType.value}"
                    )
            if screenType is ScreenType.TACTIC_FORMATION:
                tactic = self.tacticParser.parse(processed)
                return ImportResult(
                    source,
                    screenType,
                    [],
                    tacticName=tactic.name,
                    confidence=tactic.confidence,
                )
            if screenType in {
                ScreenType.TACTIC_IN_POSSESSION,
                ScreenType.TACTIC_OUT_OF_POSSESSION,
            }:
                return ImportResult(source, screenType, [])
            players = self.squadParser.parse(processed)
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
