"""High-level file inspection and placeholder tactic parser."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from fmsat.core.logUtils import getLogger

from fmsat.fmf.compression import compressionProbe
from fmsat.fmf.signatures import (
    asciiStrings,
    entropy,
    entropyWindows,
    headerInfo,
    sectionCandidates,
)
from fmsat.fmf.structures import FileInspection, PlayerSlot, TacticMetadata

LOGGER = getLogger()


@dataclass(frozen=True)
class FMFTactic:
    """Parsed tactic model.

    Most fields are intentionally optional at this stage. As byte mappings are proven, they should
    be promoted from ``unknown`` into typed properties with evidence in
    ``documentation/reverseEngineering.md``.
    """

    metadata: TacticMetadata
    formation: str | None = None
    mentality: str | None = None
    players: tuple[PlayerSlot, ...] = ()
    teamInstructions: tuple[str, ...] = ()
    playerInstructions: dict[str, tuple[str, ...]] = field(default_factory=dict)
    unknown: dict[str, int | str | bytes] = field(default_factory=dict)

    @classmethod
    def read(cls, path: str | Path) -> FMFTactic:
        return FMFParser().parse(path)


class FMFParser:
    """Entry point for inspecting and parsing FMF files."""

    def inspect(self, path: str | Path) -> FileInspection:
        filePath = Path(path)
        data = filePath.read_bytes()
        LOGGER.info("inspecting %s (%d bytes)", filePath, len(data))
        possibleOffsets = tuple(
            sorted({0, *[item.offset for item in sectionCandidates(data)[:10]]})
        )
        return FileInspection(
            path=filePath,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            header=headerInfo(data),
            entropy=entropy(data),
            entropyWindows=entropyWindows(data),
            strings=asciiStrings(data),
            sections=sectionCandidates(data),
            compressionAttempts=compressionProbe(data, offsets=possibleOffsets),
        )

    def parse(self, path: str | Path) -> FMFTactic:
        filePath = Path(path)
        data = filePath.read_bytes()
        LOGGER.info("creating low-confidence tactic model for %s", filePath)
        return FMFTactic(
            metadata=TacticMetadata(
                filename=filePath.name,
                size=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
            ),
            unknown={
                "header_hex": data[:32].hex(" "),
                "known_fields": "none-yet",
            },
        )
