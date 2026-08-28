"""Application services coordinating core components."""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
from fmsat.core.logUtils import getLogger
from fmsat.core.playerIdentity import playerEvidenceMatches, preferredPlayerName

from .detection import ScreenDetector, ScreenType
from .images import ImagePreprocessor, imageLoad
from .parser import (
    ExtractedPlayer,
    RoleProfileEvidence,
    RoleProfileParser,
    SquadAttributesParser,
    TacticParser,
)

logger = getLogger()


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
    image: np.ndarray | None = None
    additionalImages: list[np.ndarray] = field(default_factory=list)
    mergeConflicts: list[str] = field(default_factory=list)
    roleProfile: RoleProfileEvidence | None = None


def squadCapturesMerge(first: ImportResult, second: ImportResult) -> ImportResult:
    """Merge two complementary squad-attribute captures into one review result."""

    remaining = list(second.players)
    mergedPlayers: list[ExtractedPlayer] = []
    conflicts: list[str] = []
    for firstPlayer in first.players:
        match = _playerMatch(firstPlayer, remaining)
        if match is None:
            mergedPlayers.append(firstPlayer)
            continue
        remaining.remove(match)
        mergedPlayers.append(_playerMerge(firstPlayer, match, conflicts))
    mergedPlayers.extend(remaining)
    images = list(first.additionalImages)
    if second.image is not None:
        images.append(second.image.copy())
    images.extend(image.copy() for image in second.additionalImages)
    return ImportResult(
        first.source,
        first.screenType,
        mergedPlayers,
        confidence=min(first.confidence, second.confidence),
        image=first.image.copy() if first.image is not None else None,
        additionalImages=images,
        mergeConflicts=conflicts,
    )


def _playerMatch(
    player: ExtractedPlayer,
    candidates: list[ExtractedPlayer],
) -> ExtractedPlayer | None:
    matches = [candidate for candidate in candidates if playerEvidenceMatches(player, candidate)]
    return matches[0] if len(matches) == 1 else None


def _playerMerge(
    first: ExtractedPlayer,
    second: ExtractedPlayer,
    conflicts: list[str],
) -> ExtractedPlayer:
    attributes: dict[str, int | None] = {}
    for name in first.attributes.keys() | second.attributes.keys():
        firstValue = first.attributes.get(name)
        secondValue = second.attributes.get(name)
        if firstValue is not None and secondValue is not None and firstValue != secondValue:
            conflicts.append(f"{first.name}: {name} {firstValue} / {secondValue}")
        attributes[name] = firstValue if firstValue is not None else secondValue
    return ExtractedPlayer(
        name=preferredPlayerName(first, second),
        positions=_textMerge(
            first.positions,
            second.positions,
            first.name,
            "positions",
            conflicts,
        ),
        ca=_textMerge(first.ca, second.ca, first.name, "CA", conflicts),
        pa=_textMerge(first.pa, second.pa, first.name, "PA", conflicts),
        attributes=attributes,
        confidence=min(first.confidence, second.confidence),
    )


def _textMerge(
    first: str,
    second: str,
    playerName: str,
    fieldName: str,
    conflicts: list[str],
) -> str:
    firstValue = first.strip()
    secondValue = second.strip()
    if firstValue and secondValue and firstValue.casefold() != secondValue.casefold():
        conflicts.append(f"{playerName}: {fieldName} {firstValue!r} / {secondValue!r}")
    return firstValue or secondValue


def _nameNormalize(value: str) -> str:
    return " ".join(value.split()).casefold()


class ScreenshotImportService:
    """Coordinates loading, preprocessing, detection, and screen parsing."""

    def __init__(
        self,
        preprocessor: ImagePreprocessor,
        detector: ScreenDetector,
        squadParser: SquadAttributesParser,
        tacticParser: TacticParser,
        roleProfileParser: RoleProfileParser | None = None,
    ) -> None:
        self.preprocessor = preprocessor
        self.detector = detector
        self.squadParser = squadParser
        self.tacticParser = tacticParser
        self.roleProfileParser = roleProfileParser

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
                if screenType is ScreenType.UNKNOWN and expectedType is ScreenType.SQUAD_ATTRIBUTES:
                    logger.warning(
                        "Squad screen signature was incomplete; validating the requested "
                        "type through player-row extraction"
                    )
                    screenType = expectedType
                elif {screenType, expectedType}.issubset(instructionTypes):
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
                    image=image.copy(),
                )
            if screenType in {
                ScreenType.TACTIC_IN_POSSESSION,
                ScreenType.TACTIC_OUT_OF_POSSESSION,
            }:
                return ImportResult(source, screenType, [], image=image.copy())
            if screenType is ScreenType.ROLE_PROFILE:
                if self.roleProfileParser is None:
                    raise ImportError("Role-profile parsing is not configured")
                evidence = self.roleProfileParser.parse(processed)
                evidence = replace(evidence, sourceImport=source)
                return ImportResult(
                    source,
                    screenType,
                    [],
                    confidence=evidence.confidence,
                    image=image.copy(),
                    roleProfile=evidence,
                )
            players = self.squadParser.parse(processed)
            if not players:
                raise ImportError(
                    "No player rows could be extracted. Please retake the screenshot, "
                    "making sure the Player, Position, CA and PA headings and complete "
                    "player rows are visible."
                )
            return ImportResult(source, screenType, players, image=image.copy())
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
