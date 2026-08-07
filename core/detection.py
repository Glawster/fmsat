"""Screen type detection contracts and Phase 1 implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from enum import Enum

import numpy as np

from .ocr import OcrEngine


class ScreenType(str, Enum):  # noqa: UP042 - keeps local Python 3.10 verification possible
    """Known Football Manager screenshot types."""

    UNKNOWN = "UNKNOWN"
    CLUB_INFORMATION = "CLUB_INFORMATION"
    TACTIC_FORMATION = "TACTIC_FORMATION"
    TACTIC_IN_POSSESSION = "TACTIC_IN_POSSESSION"
    TACTIC_OUT_OF_POSSESSION = "TACTIC_OUT_OF_POSSESSION"
    ROLE_PROFILE = "ROLE_PROFILE"
    SQUAD_ATTRIBUTES = "SQUAD_ATTRIBUTES"


class ScreenDetector(ABC):
    """Abstract screen detector for future screen-specific implementations."""

    @abstractmethod
    def detect(self, image: np.ndarray) -> ScreenType:
        """Return the recognized screen type."""


class KeywordScreenDetector(ScreenDetector):
    """Detects supported screens from configured header keywords."""

    def __init__(
        self,
        ocr: OcrEngine,
        keywords: list[str] | dict[ScreenType, list[str]],
        minimumConfidence: float = 0.55,
    ) -> None:
        self.ocr = ocr
        if isinstance(keywords, list):
            keywords = {ScreenType.SQUAD_ATTRIBUTES: keywords}
        self.keywords = {
            screenType: {word.casefold() for word in values}
            for screenType, values in keywords.items()
        }
        self.minimumConfidence = minimumConfidence

    def detect(self, image: np.ndarray) -> ScreenType:
        """OCR the header and first instruction row, then score keyword matches."""

        header = image[: max(1, int(image.shape[0] * 0.45)), :]
        headerResults = [
            result
            for result in self.ocr.recognize(header)
            if result.confidence >= self.minimumConfidence
        ]
        recognized = Counter(
            token.casefold() for result in headerResults for token in result.text.split()
        )
        roleProfileWords = self.keywords.get(ScreenType.ROLE_PROFILE, set())
        headerText = " ".join(result.text for result in headerResults).casefold()
        if roleProfileWords and "player roles" in headerText and (
            "in possession role" in headerText or "out of possession role" in headerText
        ):
            return ScreenType.ROLE_PROFILE
        if roleProfileWords and {"key", "attributes"}.issubset(recognized) and (
            "ability" in recognized or "instructions" in recognized
        ):
            return ScreenType.ROLE_PROFILE
        keywordUseCount = {
            word: sum(word in words for words in self.keywords.values())
            for words in self.keywords.values()
            for word in words
        }
        matches = {}
        for screenType, words in self.keywords.items():
            distinctive = {word for word in words if keywordUseCount[word] == 1}
            present = distinctive & recognized.keys()
            matches[screenType] = (sum(recognized[word] for word in present), len(present))
        screenType, (score, distinctScore) = max(matches.items(), key=lambda item: item[1])
        if roleProfileWords and screenType in {
            ScreenType.TACTIC_IN_POSSESSION,
            ScreenType.TACTIC_OUT_OF_POSSESSION,
        }:
            height, width = image.shape[:2]
            detailPanel = image[int(height * 0.35) : int(height * 0.95), int(width * 0.30) :]
            detailWords = {
                token.casefold()
                for result in self.ocr.recognize(detailPanel)
                if result.confidence >= self.minimumConfidence
                for token in result.text.split()
            }
            if {"key", "attributes", "player", "instructions"}.issubset(detailWords):
                return ScreenType.ROLE_PROFILE
        requiredMatches = max(2, len(self.keywords[screenType]) // 2)
        return screenType if score and distinctScore >= requiredMatches else ScreenType.UNKNOWN
