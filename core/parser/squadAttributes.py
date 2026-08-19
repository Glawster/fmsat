"""Configuration-driven Squad Attributes table parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median
from typing import Any

import cv2
import numpy as np
from fmsat.core.logUtils import getLogger

from ..config import AttributeDefinition
from ..ocr import OcrEngine, OcrResult
from ..textCleanup import ocrTextClean
from .models import ExtractedPlayer

logger = getLogger()


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
        settings = self.regions.get("squadAttributes")
        if not isinstance(settings, dict):
            raise ParserError("Missing squadAttributes region configuration")
        if self.ocr.suppliesGeometry:
            return self._positionedParse(image)

        table = self._regionCrop(image, settings["table"])
        headerHeight = self._pixels(settings["header_height"], table.shape[0])
        rowHeight = max(1, self._pixels(settings["row_height"], table.shape[0]))
        body = table[headerHeight:, :]
        players: list[ExtractedPlayer] = []
        emptyRows = 0
        for y in range(
            0,
            max(0, body.shape[0] - rowHeight + 1),
            rowHeight,
        ):
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
        results = self._positionedResults(image)
        baseHeaders = {
            "positions": self._headerFind(results, "position"),
            "ca": self._headerFind(results, "ca"),
            "pa": self._headerFind(results, "pa"),
        }
        if any(result is None for result in baseHeaders.values()):
            logger.warning(
                "squad parser missing base headers results=%d position=%s ca=%s pa=%s",
                len(results),
                baseHeaders["positions"] is not None,
                baseHeaders["ca"] is not None,
                baseHeaders["pa"] is not None,
            )
            return []

        positionedHeaders = {
            name: result
            for name, result in baseHeaders.items()
            if result is not None
        }
        headerY = sum(
            result.center[1] for result in positionedHeaders.values()
        ) / len(positionedHeaders)
        headerTolerance = max(12.0, image.shape[0] * 0.025)
        columns = {
            name: result.center[0]
            for name, result in positionedHeaders.items()
        }
        positionGap = columns["ca"] - columns["positions"]
        if positionGap <= 0:
            return []

        playerHeader = self._headerFind(results, "player")
        columns["name"] = (
            (playerHeader.center[0] + columns["positions"]) / 2
            if playerHeader is not None
            and abs(playerHeader.center[1] - headerY) <= headerTolerance
            else max(0.0, columns["positions"] - positionGap)
        )

        attributeColumns: set[str] = set()
        for definition in self.attributes:
            header = self._attributeHeaderFind(
                results,
                definition.name,
                headerY,
                headerTolerance,
                columns["pa"],
            )
            if header is not None:
                columns[definition.name] = header.center[0]
                attributeColumns.add(definition.name)

        orderedColumns = sorted(columns.items(), key=lambda item: item[1])
        attributeXs = sorted(columns[name] for name in attributeColumns)
        attributeSpacing = (
            median(
                right - left
                for left, right in zip(attributeXs, attributeXs[1:], strict=False)
            )
            if len(attributeXs) >= 2
            else image.shape[1] * 0.04
        )
        attributeTolerance = attributeSpacing * 0.48
        rowResults = [
            result
            for result in results
            if result.center[1] > headerY + headerTolerance / 2
        ]
        assigned = []
        for result in rowResults:
            column, columnX = min(
                orderedColumns,
                key=lambda item: abs(item[1] - result.center[0]),
            )
            if (
                column in attributeColumns
                and abs(columnX - result.center[0]) > attributeTolerance
            ):
                continue
            assigned.append((result, column))

        rowSeeds = self._rowSeedsBuild(assigned)
        rowSpacings = [
            right.center[1] - left.center[1]
            for left, right in zip(rowSeeds, rowSeeds[1:], strict=False)
            if right.center[1] - left.center[1] > 8
        ]
        rowSpacing = median(rowSpacings) if rowSpacings else image.shape[0] * 0.025
        rowTolerance = max(
            10.0,
            min(rowSpacing * 0.42, image.shape[0] * 0.022),
        )

        focusedNames = self._focusedNameResults(
            image,
            playerHeader,
            columns["positions"],
            headerY,
        )
        focusedRows = {
            index
            for result in focusedNames
            for index, rowSeed in enumerate(rowSeeds)
            if abs(result.center[1] - rowSeed.center[1]) <= rowTolerance
        }
        minimumNameCoverage = max(1, int(len(rowSeeds) * 0.7))
        if len(focusedRows) >= minimumNameCoverage:
            assigned = [
                item
                for item in assigned
                if item[1] != "name"
                or not any(
                    abs(item[0].center[1] - rowSeeds[index].center[1])
                    <= rowTolerance
                    for index in focusedRows
                )
            ]
            assigned.extend(
                (result, "name")
                for result in focusedNames
                if any(
                    abs(result.center[1] - rowSeeds[index].center[1])
                    <= rowTolerance
                    for index in focusedRows
                )
            )

        players: list[ExtractedPlayer] = []
        previousY = -1.0
        for rowSeed in rowSeeds:
            rowY = rowSeed.center[1]
            if rowY - previousY < max(6.0, image.shape[0] * 0.008):
                continue
            previousY = rowY
            rowCells: dict[str, list[OcrResult]] = {}
            for result, column in assigned:
                if abs(result.center[1] - rowY) <= rowTolerance:
                    rowCells.setdefault(column, []).append(result)

            cells: dict[str, _Cell] = {}
            for name, values in rowCells.items():
                if name in attributeColumns:
                    cells[name] = self._positionedAttributeCellRead(values, columns[name])
                else:
                    cells[name] = self._positionedCellRead(
                        [
                            self._playerNameResultClean(value)
                            if name == "name"
                            else value
                            for value in values
                            if name != "name"
                            or self._playerNameFragmentValid(value.text)
                        ]
                    )

            if "name" not in cells or not cells["name"].text.strip():
                recoveredName = self._focusedNameRead(
                    image,
                    playerHeader,
                    columns["positions"],
                    rowY,
                    rowTolerance,
                )
                if recoveredName.text:
                    cells["name"] = recoveredName

            for attributeName in attributeColumns:
                parsed = self._attributeParse(
                    cells.get(attributeName, _Cell("", 0.0)).text
                )
                observedValues = {
                    value
                    for value in (
                        self._attributeParse(result.text)
                        for result in rowCells.get(attributeName, ())
                    )
                    if value is not None
                }
                if parsed is not None and len(observedValues) <= 1:
                    continue
                recovered = self._focusedAttributeRead(
                    image,
                    columns[attributeName],
                    rowY,
                    attributeSpacing,
                    rowTolerance,
                )
                if recovered.text:
                    cells[attributeName] = recovered

            if (
                "name" not in cells
                or not cells["name"].text.strip()
                or not self._numericCellValid(cells.get("ca"))
                or not self._numericCellValid(cells.get("pa"))
            ):
                continue

            populated = [cell for cell in cells.values() if cell.text]
            confidence = (
                sum(cell.confidence for cell in populated) / len(populated)
                if populated
                else 0.0
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
                        if definition.name in attributeColumns
                    },
                    confidence=confidence,
                )
            )

        logger.info(
            "squad parser results=%d attributes=%d assigned=%d rowSeeds=%d "
            "focusedNames=%d rowTolerance=%.1f players=%d",
            len(results),
            len(attributeColumns),
            len(assigned),
            len(rowSeeds),
            len(focusedNames),
            rowTolerance,
            len(players),
        )
        return players

    def _rowSeedsBuild(
        self,
        assigned: list[tuple[OcrResult, str]],
    ) -> list[OcrResult]:
        """Build one row seed from either CA or PA evidence, preferring CA when both exist."""

        candidates = sorted(
            (
                (result, column)
                for result, column in assigned
                if column in {"ca", "pa"}
                and re.fullmatch(r"\d{1,3}", result.text.strip()) is not None
            ),
            key=lambda item: item[0].center[1],
        )
        groups: list[list[tuple[OcrResult, str]]] = []
        for candidate in candidates:
            if not groups or abs(candidate[0].center[1] - groups[-1][0][0].center[1]) > 8:
                groups.append([candidate])
            else:
                groups[-1].append(candidate)
        return [
            next(
                (result for result, column in group if column == "ca"),
                group[0][0],
            )
            for group in groups
        ]

    def _positionedResults(self, image: np.ndarray) -> list[OcrResult]:
        height, width = image.shape[:2]
        if height < 700 or width < 1200:
            return [
                result
                for result in self.ocr.recognize(image)
                if result.center is not None
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
            scale = 1.5
            enlarged = cv2.resize(
                image[top:bottom, :],
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC,
            )
            for result in self.ocr.recognize(enlarged):
                if result.bounds is None:
                    continue
                left, localTop, right, localBottom = result.bounds
                translated = OcrResult(
                    result.text,
                    result.confidence,
                    (
                        left / scale,
                        localTop / scale + top,
                        right / scale,
                        localBottom / scale + top,
                    ),
                )
                if not self._resultDuplicate(positioned, translated):
                    positioned.append(translated)
        return positioned

    def _focusedNameResults(
        self,
        image: np.ndarray,
        playerHeader: OcrResult | None,
        positionX: float,
        headerY: float,
    ) -> list[OcrResult]:
        if playerHeader is None or playerHeader.center is None:
            return []
        height, width = image.shape[:2]
        playerX = playerHeader.center[0]
        gap = positionX - playerX
        if gap <= 0:
            return []
        headerLeft = (
            playerHeader.bounds[0]
            if playerHeader.bounds is not None
            else playerX
        )
        left = max(0, int(min(playerX, headerLeft)))
        right = min(width, int(positionX - gap * 0.10))
        top = max(0, int(headerY + height * 0.012))
        if right <= left or top >= height:
            return []

        scale = 2.0
        enlarged = cv2.resize(
            image[top:, left:right],
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )
        names = []
        for result in self.ocr.recognize(enlarged):
            if result.bounds is None:
                continue
            localLeft, localTop, localRight, localBottom = result.bounds
            translated = OcrResult(
                result.text,
                result.confidence,
                (
                    localLeft / scale + left,
                    localTop / scale + top,
                    localRight / scale + left,
                    localBottom / scale + top,
                ),
            )
            if self._playerNameFragmentValid(translated.text):
                names.append(translated)
        return names

    def _focusedNameRead(
        self,
        image: np.ndarray,
        playerHeader: OcrResult | None,
        positionX: float,
        rowY: float,
        rowTolerance: float,
    ) -> _Cell:
        """Retry only a missing player name using a tightly cropped enlarged row cell."""

        if playerHeader is None or playerHeader.center is None:
            return _Cell("", 0.0)
        height, width = image.shape[:2]
        playerX = playerHeader.center[0]
        gap = positionX - playerX
        if gap <= 0:
            return _Cell("", 0.0)
        left = max(0, int(playerHeader.bounds[0] if playerHeader.bounds is not None else playerX))
        right = min(width, int(positionX - gap * 0.08))
        top = max(0, int(rowY - rowTolerance * 0.9))
        bottom = min(height, int(rowY + rowTolerance * 0.9))
        if right <= left or bottom <= top:
            return _Cell("", 0.0)

        scale = 3.0
        enlarged = cv2.resize(
            image[top:bottom, left:right],
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )
        results = [
            result
            for result in self.ocr.recognize(enlarged)
            if self._playerNameFragmentValid(result.text)
        ]
        if not results:
            return _Cell("", 0.0)
        cleaned = [self._playerNameResultClean(result) for result in results]
        return self._positionedCellRead(cleaned)

    def _focusedAttributeRead(
        self,
        image: np.ndarray,
        columnX: float,
        rowY: float,
        spacing: float,
        rowTolerance: float,
    ) -> _Cell:
        """Retry a missing or conflicting numeric attribute in a tightly cropped cell."""

        height, width = image.shape[:2]
        halfWidth = max(10.0, spacing * 0.34)
        top = max(0, int(rowY - rowTolerance * 0.85))
        bottom = min(height, int(rowY + rowTolerance * 0.85))
        left = max(0, int(columnX - halfWidth))
        right = min(width, int(columnX + halfWidth))
        if right <= left or bottom <= top:
            return _Cell("", 0.0)

        scale = 3.0
        enlarged = cv2.resize(
            image[top:bottom, left:right],
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )
        candidates = [
            result
            for result in self.ocr.recognize(enlarged)
            if self._attributeParse(result.text) is not None
        ]
        if not candidates:
            return _Cell("", 0.0)
        best = max(candidates, key=lambda result: result.confidence)
        return _Cell(best.text.strip(), best.confidence)

    def _resultDuplicate(
        self,
        results: list[OcrResult],
        candidate: OcrResult,
    ) -> bool:
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

    @staticmethod
    def _playerNameFragmentValid(value: str) -> bool:
        cleaned = SquadAttributesParser._playerNameTextClean(value)
        return (
            len("".join(character for character in cleaned if character.isalpha()))
            >= 3
        )

    @staticmethod
    def _playerNameTextClean(value: str) -> str:
        cleaned = value.strip()
        cleaned = re.sub(r"^[a-z](?=[A-Z][a-z])", "", cleaned)
        cleaned = re.sub(r"^[A-Z]{2}(?=[A-Z][a-z])", "", cleaned)
        return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cleaned)

    @classmethod
    def _playerNameResultClean(cls, result: OcrResult) -> OcrResult:
        return OcrResult(
            cls._playerNameTextClean(result.text),
            result.confidence,
            result.bounds,
        )

    def _headerFind(
        self,
        results: list[OcrResult],
        expected: str,
    ) -> OcrResult | None:
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
        attributeName: str,
        headerY: float,
        tolerance: float,
        minimumX: float,
    ) -> OcrResult | None:
        """Match FM's full attribute heading, allowing UI ellipsis truncation."""

        expected = self._tokenNormalize(attributeName)
        matches = []
        for result in results:
            if (
                abs(result.center[1] - headerY) > tolerance
                or result.center[0] <= minimumX
            ):
                continue
            observed = self._tokenNormalize(result.text)
            if not observed:
                continue
            if observed == expected or (
                len(observed) >= 3 and expected.startswith(observed)
            ):
                matches.append(result)
        return min(matches, key=lambda result: result.center[0], default=None)

    def _positionedCellRead(self, results: list[OcrResult]) -> _Cell:
        """Read one cell while discarding lower-confidence overlapping OCR duplicates."""

        selected: list[OcrResult] = []
        for result in sorted(results, key=lambda item: item.confidence, reverse=True):
            if result.bounds is None:
                selected.append(result)
                continue
            left, _, right, _ = result.bounds
            width = max(1.0, right - left)
            overlaps = False
            for existing in selected:
                if existing.bounds is None:
                    continue
                existingLeft, _, existingRight, _ = existing.bounds
                intersection = max(0.0, min(right, existingRight) - max(left, existingLeft))
                if intersection / min(width, max(1.0, existingRight - existingLeft)) >= 0.5:
                    overlaps = True
                    break
            if not overlaps:
                selected.append(result)

        ordered, seenTokens = [], set()
        for result in sorted(selected, key=lambda item: item.center[0] if item.center else 0.0):
            token = self._tokenNormalize(result.text)
            if token and token in seenTokens:
                continue
            seenTokens.add(token)
            ordered.append(result)
        if not ordered:
            return _Cell("", 0.0)
        return _Cell(
            ocrTextClean(" ".join(result.text for result in ordered)),
            sum(result.confidence for result in ordered) / len(ordered),
        )

    def _positionedAttributeCellRead(
        self,
        results: list[OcrResult],
        columnX: float,
    ) -> _Cell:
        """Choose one numeric OCR candidate instead of concatenating overlapping fragments."""

        candidates = [
            result
            for result in results
            if result.center is not None and self._attributeParse(result.text) is not None
        ]
        if not candidates:
            return _Cell("", 0.0)
        best = min(
            candidates,
            key=lambda result: (
                abs(result.center[0] - columnX),
                -result.confidence,
            ),
        )
        return _Cell(best.text.strip(), best.confidence)

    @staticmethod
    def _numericCellValid(cell: _Cell | None) -> bool:
        return (
            cell is not None
            and re.fullmatch(r"\d{1,3}", cell.text.strip()) is not None
        )

    def _attributeParse(self, text: str) -> int | None:
        digits = "".join(character for character in text if character.isdigit())
        if not digits:
            return None
        value = int(digits)
        return value if 1 <= value <= 20 else None

    def _cellRead(self, row: np.ndarray, x: float, width: float) -> _Cell:
        """Read one configured row cell using the YAML `x`/`width` contract."""

        left = self._pixels(x, row.shape[1])
        right = min(
            row.shape[1],
            left + self._pixels(width, row.shape[1]),
        )
        results = self.ocr.recognize(row[:, left:right])
        if not results:
            return _Cell("", 0.0)
        return _Cell(
            ocrTextClean(" ".join(result.text for result in results)),
            sum(result.confidence for result in results) / len(results),
        )

    def _pixels(self, normalized: float, total: int) -> int:
        return int(round(float(normalized) * total))

    def _regionCrop(
        self,
        image: np.ndarray,
        region: dict[str, float],
    ) -> np.ndarray:
        height, width = image.shape[:2]
        left = self._pixels(region["x"], width)
        top = self._pixels(region["y"], height)
        right = min(
            width,
            left + self._pixels(region["width"], width),
        )
        bottom = min(
            height,
            top + self._pixels(region["height"], height),
        )
        if right <= left or bottom <= top:
            raise ParserError("Configured table region is empty")
        return image[top:bottom, left:right]

    def _rowParse(
        self,
        row: np.ndarray,
        settings: dict[str, Any],
    ) -> ExtractedPlayer:
        columns = settings["columns"]
        name = self._cellRead(row, **columns["name"])
        positions = self._cellRead(row, **columns["positions"])
        ca = self._cellRead(row, **columns["ca"])
        pa = self._cellRead(row, **columns["pa"])
        attributeArea = settings["attribute_area"]
        attributeWidth = attributeArea["width"] / max(1, len(self.attributes))
        attributes = {}
        confidences = [
            name.confidence,
            positions.confidence,
            ca.confidence,
            pa.confidence,
        ]
        for index, definition in enumerate(self.attributes):
            cell = self._cellRead(
                row,
                attributeArea["x"] + index * attributeWidth,
                attributeWidth,
            )
            attributes[definition.name] = self._attributeParse(cell.text)
            confidences.append(cell.confidence)
        populated = [value for value in confidences if value > 0]
        confidence = (
            sum(populated) / len(populated)
            if populated
            else 0.0
        )
        return ExtractedPlayer(
            name=ocrTextClean(name.text),
            positions=ocrTextClean(positions.text),
            ca=ocrTextClean(ca.text),
            pa=ocrTextClean(pa.text),
            attributes=attributes,
            confidence=confidence,
        )