"""Extract tactic-level metadata from a Football Manager formation screenshot."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import cv2

from fmsat.core.ocr import OcrEngine
from fmsat.core.textCleanup import ocrTextClean


@dataclass(frozen=True, slots=True)
class TacticMetadataExtractResult:
    """Tactic metadata and any evidence that could not be captured."""

    metadata: dict[str, str]
    issues: tuple[str, ...]


class TacticMetadataExtractor:
    """Read tactic-level metadata from the saved Formation screen.

    The formation/template label displayed by Football Manager is deliberately
    ignored. FMSAT owns tactic identity, and the two object-model formations are
    derived from that identity as ``<tactic name> IP`` and ``<tactic name> OOP``.
    """

    _MENTALITIES = (
        "Very Defensive",
        "Cautious",
        "Defensive",
        "Balanced",
        "Positive",
        "Very Attacking",
        "Attacking",
    )

    def __init__(self, ocr: OcrEngine) -> None:
        self.ocr = ocr

    ## metadata

    def metadataExtract(self, imageFilename: str) -> TacticMetadataExtractResult:
        """Return tactic-level metadata recognized from one persisted screenshot."""

        imagePath = Path(imageFilename).expanduser()
        if not imagePath.is_file():
            return TacticMetadataExtractResult(
                {},
                (f"Formation screenshot is unavailable: {imageFilename}",),
            )

        image = cv2.imread(str(imagePath), cv2.IMREAD_COLOR)
        if image is None:
            return TacticMetadataExtractResult(
                {},
                (f"Formation screenshot could not be decoded: {imageFilename}",),
            )

        try:
            results = self.ocr.recognize(image)
        except Exception as exc:
            return TacticMetadataExtractResult({}, (f"Formation metadata OCR failed: {exc}",))

        fragments = [ocrTextClean(result.text) for result in results if result.text.strip()]
        metadata: dict[str, str] = {}

        mentality = self._mentalityExtract(fragments)
        if mentality:
            metadata["mentality"] = mentality

        issues = (
            ("Formation screenshot did not expose mentality",)
            if not mentality
            else ()
        )
        return TacticMetadataExtractResult(metadata, issues)

    ## parsing

    @classmethod
    def _mentalityExtract(cls, fragments: list[str]) -> str:
        """Return the standard FM mentality label found in recognized text."""

        for mentality in cls._MENTALITIES:
            pattern = re.compile(rf"\b{re.escape(mentality)}\b", re.IGNORECASE)
            if any(pattern.search(fragment) for fragment in fragments):
                return mentality.casefold().replace(" ", "")
        return ""
