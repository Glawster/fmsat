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
    """Formation metadata and any evidence that could not be captured."""

    metadata: dict[str, str]
    issues: tuple[str, ...]


class TacticMetadataExtractor:
    """Read formation name and mentality from the saved Formation screen."""

    _FORMATION_PATTERN = re.compile(
        r"(?<!\d)([1-5](?:\s*[-\u2013\u2014]\s*[1-5]){2,4}"
        r"(?:\s+(?:DM|AM|WIDE|NARROW)){0,4})(?!\d)",
        re.IGNORECASE,
    )
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
        """Return metadata recognized from one persisted screenshot file."""

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

        formationName = self._formationNameExtract(fragments)
        if formationName:
            metadata["formationName"] = formationName

        mentality = self._mentalityExtract(fragments)
        if mentality:
            metadata["mentality"] = mentality

        missing = []
        if not formationName:
            missing.append("formation name")
        if not mentality:
            missing.append("mentality")
        issues = (
            (f"Formation screenshot did not expose {self._listJoin(missing)}",)
            if missing
            else ()
        )
        return TacticMetadataExtractResult(metadata, issues)

    ## parsing

    @classmethod
    def _formationNameExtract(cls, fragments: list[str]) -> str:
        """Select the most descriptive formation notation recognized by OCR."""

        candidates: list[str] = []
        for fragment in fragments:
            for match in cls._FORMATION_PATTERN.finditer(fragment):
                value = re.sub(r"\s*[-\u2013\u2014]\s*", "-", match.group(1))
                words = value.split()
                suffixes = {
                    "dm": "DM",
                    "am": "AM",
                    "wide": "Wide",
                    "narrow": "Narrow",
                }
                candidates.append(
                    " ".join(words[:1] + [suffixes[word.casefold()] for word in words[1:]])
                )
        return max(candidates, key=lambda value: (len(value.split()), len(value)), default="")

    @classmethod
    def _mentalityExtract(cls, fragments: list[str]) -> str:
        """Return the standard FM mentality label found in recognized text."""

        for mentality in cls._MENTALITIES:
            pattern = re.compile(rf"\b{re.escape(mentality)}\b", re.IGNORECASE)
            if any(pattern.search(fragment) for fragment in fragments):
                return mentality.casefold().replace(" ", "")
        return ""

    @staticmethod
    def _listJoin(values: list[str]) -> str:
        """Render one or two missing field labels naturally."""

        if len(values) < 2:
            return values[0] if values else "metadata"
        return " and ".join(values)
