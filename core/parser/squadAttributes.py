"""Configuration-driven Squad Attributes table parser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..config import AttributeDefinition
from ..ocr import OcrEngine
from .models import ExtractedPlayer


class ParserError(RuntimeError):
    """Raised when the supported screen cannot be parsed safely."""


@dataclass(frozen=True, slots=True)
class _Cell:
    text: str
    confidence: float


class SquadAttributesParser:
    """Extracts table rows using normalized YAML region coordinates."""

    def __init__(
        self,
        ocr: OcrEngine,
        regions: dict[str, Any],
        attributes: tuple[AttributeDefinition, ...],
        maximumEmptyRows: int = 3,
    ) -> None:
        self.ocr = ocr
        self.regions = regions
        self.attributes = attributes
        self.maximumEmptyRows = maximumEmptyRows

    def parse(self, image: np.ndarray) -> list[ExtractedPlayer]:
        """Extract all visible player rows from a Squad Attributes screenshot."""

        settings = self.regions.get("squadAttributes")
        if not isinstance(settings, dict):
            raise ParserError("Missing squadAttributes region configuration")
        table = self._regionCrop(image, settings["table"])
        headerHeight = self._pixels(settings["header_height"], table.shape[0])
        rowHeight = max(1, self._pixels(settings["row_height"], table.shape[0]))
        body = table[headerHeight:, :]
        players: list[ExtractedPlayer] = []
        emptyRows = 0
        for y in range(0, max(0, body.shape[0] - rowHeight + 1), rowHeight):
            row = body[y : y + rowHeight, :]
            player = self._rowParse(row, settings)
            if not player.name.strip():
                emptyRows += 1
                if emptyRows >= self.maximumEmptyRows:
                    break
                continue
            emptyRows = 0
            players.append(player)
        return players

    def _attributeParse(self, text: str) -> int | None:
        digits = "".join(character for character in text if character.isdigit())
        if not digits:
            return None
        value = int(digits)
        return value if 1 <= value <= 20 else None

    def _cellRead(self, row: np.ndarray, start: float, width: float) -> _Cell:
        left = self._pixels(start, row.shape[1])
        right = min(row.shape[1], left + self._pixels(width, row.shape[1]))
        results = self.ocr.recognize(row[:, left:right])
        if not results:
            return _Cell("", 0.0)
        return _Cell(
            " ".join(result.text for result in results),
            sum(result.confidence for result in results) / len(results),
        )

    def _pixels(self, normalized: float, total: int) -> int:
        return int(round(float(normalized) * total))

    def _regionCrop(self, image: np.ndarray, region: dict[str, float]) -> np.ndarray:
        height, width = image.shape[:2]
        left = self._pixels(region["x"], width)
        top = self._pixels(region["y"], height)
        right = min(width, left + self._pixels(region["width"], width))
        bottom = min(height, top + self._pixels(region["height"], height))
        if right <= left or bottom <= top:
            raise ParserError("Configured table region is empty")
        return image[top:bottom, left:right]

    def _rowParse(self, row: np.ndarray, settings: dict[str, Any]) -> ExtractedPlayer:
        cells = {
            name: self._cellRead(row, float(region["x"]), float(region["width"]))
            for name, region in settings["columns"].items()
        }
        area = settings["attribute_area"]
        attributeWidth = float(area["width"]) / max(1, len(self.attributes))
        attributeCells = [
            self._cellRead(row, float(area["x"]) + index * attributeWidth, attributeWidth)
            for index in range(len(self.attributes))
        ]
        confidences = [cell.confidence for cell in cells.values() if cell.text]
        confidences.extend(cell.confidence for cell in attributeCells if cell.text)
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return ExtractedPlayer(
            name=cells["name"].text,
            positions=cells["positions"].text,
            ca=cells["ca"].text,
            pa=cells["pa"].text,
            attributes={
                definition.name: self._attributeParse(cell.text)
                for definition, cell in zip(self.attributes, attributeCells, strict=True)
            },
            confidence=confidence,
        )
