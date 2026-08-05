"""Configuration-driven Squad Attributes table parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..config import AttributeDefinition
from ..ocr import OcrEngine, OcrResult
from ..textCleanup import ocrTextClean
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
        if self.ocr.suppliesGeometry:
            positionedPlayers = self._positionedParse(image)
            if positionedPlayers:
                return positionedPlayers
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

    def _positionedParse(self, image: np.ndarray) -> list[ExtractedPlayer]:
        """Map visible values by OCR header and row coordinates."""

        results = self._positionedResults(image)
        baseHeaders = {
            "positions": self._headerFind(results, "position"),
            "ca": self._headerFind(results, "ca"),
            "pa": self._headerFind(results, "pa"),
        }
        if any(result is None for result in baseHeaders.values()):
            return []
        positionedHeaders = {
            name: result for name, result in baseHeaders.items() if result is not None
        }
        headerY = sum(result.center[1] for result in positionedHeaders.values()) / len(
            positionedHeaders
        )
        headerTolerance = max(12.0, image.shape[0] * 0.025)
        columns: dict[str, float] = {
            name: result.center[0] for name, result in positionedHeaders.items()
        }
        positionGap = columns["ca"] - columns["positions"]
        if positionGap <= 0:
            return []
        columns["name"] = max(0.0, columns["positions"] - positionGap)
        for definition in self.attributes:
            header = self._attributeHeaderFind(
                results,
                definition.abbreviation,
                headerY,
                headerTolerance,
                columns["pa"],
            )
            if header is not None:
                columns[definition.name] = header.center[0]
        orderedColumns = sorted(columns.items(), key=lambda item: item[1])
        rowResults = [
            result
            for result in results
            if result.center[1] > headerY + headerTolerance / 2
        ]
        assigned = [
            (result, min(orderedColumns, key=lambda item: abs(item[1] - result.center[0]))[0])
            for result in rowResults
        ]
        nameSeeds = sorted(
            (
                result
                for result, column in assigned
                if column == "name" and any(character.isalpha() for character in result.text)
            ),
            key=lambda result: result.center[1],
        )
        players: list[ExtractedPlayer] = []
        previousY = -1.0
        for nameSeed in nameSeeds:
            rowY = nameSeed.center[1]
            if rowY - previousY < max(6.0, image.shape[0] * 0.008):
                continue
            previousY = rowY
            rowTolerance = max(
                8.0,
                (nameSeed.bounds[3] - nameSeed.bounds[1]) * 0.9,
                image.shape[0] * 0.012,
            )
            rowCells: dict[str, list[OcrResult]] = {}
            for result, column in assigned:
                if abs(result.center[1] - rowY) <= rowTolerance:
                    rowCells.setdefault(column, []).append(result)
            cells = {
                name: self._positionedCellRead(values)
                for name, values in rowCells.items()
            }
            if "name" not in cells or not self._numericCellValid(cells.get("ca")):
                continue
            if not self._numericCellValid(cells.get("pa")):
                continue
            populated = [cell for cell in cells.values() if cell.text]
            confidence = (
                sum(cell.confidence for cell in populated) / len(populated) if populated else 0.0
            )
            players.append(
                ExtractedPlayer(
                    name=cells["name"].text,
                    positions=cells.get("positions", _Cell("", 0.0)).text,
                    ca=cells["ca"].text,
                    pa=cells["pa"].text,
                    attributes={
                        definition.name: self._attributeParse(
                            cells.get(definition.name, _Cell("", 0.0)).text
                        )
                        for definition in self.attributes
                    },
                    confidence=confidence,
                )
            )
        return players

    def _positionedResults(self, image: np.ndarray) -> list[OcrResult]:
        """OCR dense squad tables in overlapping strips and restore image coordinates."""

        height, width = image.shape[:2]
        if height < 700 or width < 1200:
            return [
                result for result in self.ocr.recognize(image) if result.center is not None
            ]

        stripCount = 4
        overlap = max(32, int(height * 0.055))
        stripHeight = height / stripCount
        strips = tuple(
            (
                max(0, int(index * stripHeight) - overlap),
                min(height, int((index + 1) * stripHeight) + overlap),
            )
            for index in range(stripCount)
        )
        positioned: list[OcrResult] = []
        for top, bottom in strips:
            for result in self.ocr.recognize(image[top:bottom, :]):
                if result.bounds is None:
                    continue
                left, localTop, right, localBottom = result.bounds
                translated = OcrResult(
                    result.text,
                    result.confidence,
                    (left, localTop + top, right, localBottom + top),
                )
                if not self._resultDuplicate(positioned, translated):
                    positioned.append(translated)
        return positioned

    def _resultDuplicate(
        self,
        results: list[OcrResult],
        candidate: OcrResult,
    ) -> bool:
        """Identify the same OCR fragment seen in both overlapping strips."""

        candidateCenter = candidate.center
        if candidateCenter is None:
            return False
        candidateToken = self._tokenNormalize(candidate.text)
        for result in reversed(results):
            center = result.center
            if center is None:
                continue
            if center[1] < candidateCenter[1] - 8:
                break
            if (
                self._tokenNormalize(result.text) == candidateToken
                and abs(center[0] - candidateCenter[0]) <= 8
                and abs(center[1] - candidateCenter[1]) <= 8
            ):
                return True
        return False

    @staticmethod
    def _tokenNormalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.casefold())

    def _headerFind(self, results: list[OcrResult], expected: str) -> OcrResult | None:
        expectedToken = self._tokenNormalize(expected)
        matches = [
            result
            for result in results
            if self._tokenNormalize(result.text) == expectedToken
        ]
        return min(matches, key=lambda result: result.center[1], default=None)

    def _attributeHeaderFind(
        self,
        results: list[OcrResult],
        abbreviation: str,
        headerY: float,
        tolerance: float,
        minimumX: float,
    ) -> OcrResult | None:
        expected = self._tokenNormalize(abbreviation)
        matches = [
            result
            for result in results
            if abs(result.center[1] - headerY) <= tolerance
            and result.center[0] > minimumX
            and self._tokenNormalize(result.text).startswith(expected)
        ]
        return min(matches, key=lambda result: result.center[0], default=None)

    def _positionedCellRead(self, results: list[OcrResult]) -> _Cell:
        ordered = sorted(results, key=lambda result: result.center[0])
        return _Cell(
            ocrTextClean(" ".join(result.text for result in ordered)),
            sum(result.confidence for result in ordered) / len(ordered),
        )

    @staticmethod
    def _numericCellValid(cell: _Cell | None) -> bool:
        return cell is not None and any(character.isdigit() for character in cell.text)

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
            ocrTextClean(" ".join(result.text for result in results)),
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
