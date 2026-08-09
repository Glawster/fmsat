"""Detached records returned to FMSAT UI and service layers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TacticRecord:
    """Management-list details for one tactic."""

    name: str
    captureCount: int
    formationImage: str | None


@dataclass(frozen=True, slots=True)
class TacticDetailRecord:
    """Stored facts needed to describe one tactic without running OCR."""

    name: str
    capturedScreenTypes: tuple[str, ...]
    captureCount: int
    assignedSquads: tuple[str, ...]
    updatedAt: datetime | None


@dataclass(frozen=True, slots=True)
class SquadRecord:
    """Management-list details for one squad."""

    name: str
    captureCount: int
    playerCount: int
    clubImage: str | None = None


@dataclass(frozen=True, slots=True)
class SquadPlayerRecord:
    """One stored player snapshot with source-image provenance."""

    name: str
    positions: str
    ca: str
    pa: str
    confidence: float
    importedAt: datetime
    imageFilename: str


@dataclass(frozen=True, slots=True)
class DeletionRecord:
    """Result of a confirmed database deletion."""

    deletedCount: int
    imageFilenames: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SquadCleanupRecord:
    """Outcome of a conservative persisted-squad cleanup."""

    correctedCount: int
    mergedCount: int
    ambiguousCount: int
    remainingCount: int
