"""Dataclasses that describe known and unknown FMF structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True)
class EntropyWindow:
    offset: int
    length: int
    entropy: float
    classification: str


@dataclass(frozen=True)
class ASCIIString:
    offset: int
    value: str


@dataclass(frozen=True)
class HeaderInfo:
    magicHex: str
    magicAscii: str
    version: str | None
    flags: dict[str, int | str] = field(default_factory=dict)


@dataclass(frozen=True)
class SectionCandidate:
    offset: int
    length: int
    confidence: float
    reason: str


@dataclass(frozen=True)
class CompressionAttempt:
    algorithm: str
    offset: int
    inputLength: int
    success: bool
    outputLength: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class Change:
    offset: int
    old: int | None
    new: int | None


@dataclass(frozen=True)
class ChangeGroup:
    start: int
    end: int
    changes: tuple[Change, ...]
    likelyStructure: str


@dataclass(frozen=True)
class RepeatedStructureCandidate:
    offset: int
    recordLength: int
    count: int
    confidence: float
    reason: str


@dataclass(frozen=True)
class TacticMetadata:
    filename: str
    size: int
    sha256: str


@dataclass(frozen=True)
class PlayerSlot:
    position: str
    role: str | None = None
    duty: str | None = None
    raw: dict[str, int | str] = field(default_factory=dict)


@dataclass(frozen=True)
class FileInspection:
    path: Path
    size: int
    sha256: str
    header: HeaderInfo
    entropy: float
    entropyWindows: tuple[EntropyWindow, ...]
    strings: tuple[ASCIIString, ...]
    sections: tuple[SectionCandidate, ...]
    compressionAttempts: tuple[CompressionAttempt, ...]


@dataclass(frozen=True)
class AssetReference:
    """Reference from one Unity asset record to another known or external asset."""

    pathId: int | None = None
    assetPath: str | None = None
    assetType: str | None = None
    assetName: str | None = None
    relationship: str | None = None
    external: str | None = None


@dataclass(frozen=True)
class BundleInfo:
    """Summary metadata for a Unity asset bundle."""

    path: Path
    filename: str
    size: int
    signature: str
    unityVersion: str | None
    assetCount: int
    externalReferences: tuple[str, ...] = ()


@dataclass(frozen=True)
class AssetInfo:
    """Application-owned description of one asset inside a Unity bundle."""

    bundlePath: Path
    pathId: int
    assetType: str
    assetName: str | None = None
    serializedSize: int | None = None
    containerPath: str | None = None
    dependencies: tuple[AssetReference, ...] = ()
    externalReferences: tuple[str, ...] = ()


@dataclass(frozen=True)
class AssetData:
    """Safely readable content for an asset, or a clear unsupported message."""

    asset: AssetInfo
    representation: str
    text: str | None = None
    structure: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    message: str | None = None
