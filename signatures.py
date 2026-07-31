"""Heuristics for identifying FMF files and possible binary sections."""

from __future__ import annotations

import logging
import math
import re
from collections.abc import Iterable

from fmsat.structures import ASCIIString, EntropyWindow, HeaderInfo, SectionCandidate

LOGGER = logging.getLogger(__name__)


def entropy(data: bytes) -> float:
    """Return Shannon entropy in bits per byte."""

    if not data:
        return 0.0
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    total = len(data)
    return -sum((count / total) * math.log2(count / total) for count in counts if count)


def entropyWindows(
    data: bytes, windowSize: int = 256, step: int | None = None
) -> tuple[EntropyWindow, ...]:
    """Scan a file for high-entropy compressed regions and low-entropy tables."""

    if windowSize <= 0:
        raise ValueError("window_size must be positive")
    step = step or windowSize
    windows: list[EntropyWindow] = []
    for offset in range(0, len(data), step):
        chunk = data[offset : offset + windowSize]
        if not chunk:
            continue
        value = entropy(chunk)
        if value >= 7.4:
            classification = "likely compressed/encrypted"
        elif value <= 4.5:
            classification = "likely structured/string table"
        else:
            classification = "mixed/unknown"
        windows.append(
            EntropyWindow(
                offset=offset, length=len(chunk), entropy=value, classification=classification
            )
        )
    return tuple(windows)


def headerInfo(data: bytes) -> HeaderInfo:
    """Extract low-confidence header information from observed bytes."""

    observedFmfPrefix = bytes.fromhex("02016166652e")
    magic = data[:8]
    magicAscii = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in magic)
    flags: dict[str, int | str] = {}
    version: str | None = None

    if data.startswith(observedFmfPrefix):
        flags["signature"] = "observed-fmf-prefix"
        version = f"{data[0]}.{data[1]}"
    if len(data) >= 16:
        flags["u32_le_at_8"] = int.from_bytes(data[8:12], "little")
        flags["u32_le_at_12"] = int.from_bytes(data[12:16], "little")

    return HeaderInfo(magicHex=magic.hex(" "), magicAscii=magicAscii, version=version, flags=flags)


def asciiStrings(data: bytes, minimum: int = 4) -> tuple[ASCIIString, ...]:
    """Find printable ASCII strings with offsets."""

    pattern = rb"[\x20-\x7e]{" + str(minimum).encode("ascii") + rb",}"
    strings = [
        ASCIIString(offset=match.start(), value=match.group().decode("ascii", errors="replace"))
        for match in re.finditer(pattern, data)
    ]
    LOGGER.debug("found %d ASCII strings", len(strings))
    return tuple(strings)


def sectionCandidates(data: bytes) -> tuple[SectionCandidate, ...]:
    """Return tentative section offsets discovered from simple length-table heuristics."""

    candidates: list[SectionCandidate] = []
    size = len(data)
    for offset in range(0, max(0, min(size - 4, 512))):
        length = int.from_bytes(data[offset : offset + 4], "little")
        if 0 < length <= size - offset - 4:
            confidence = 0.35
            reason = "little-endian length points inside file"
            if offset % 4 == 0:
                confidence += 0.1
                reason += "; aligned"
            candidates.append(
                SectionCandidate(
                    offset=offset + 4,
                    length=length,
                    confidence=min(confidence, 0.95),
                    reason=reason,
                )
            )
    return tuple(_sectionsDeduplicate(candidates))


def _sectionsDeduplicate(candidates: Iterable[SectionCandidate]) -> list[SectionCandidate]:
    best: dict[tuple[int, int], SectionCandidate] = {}
    for candidate in candidates:
        key = (candidate.offset, candidate.length)
        previous = best.get(key)
        if previous is None or candidate.confidence > previous.confidence:
            best[key] = candidate
    return sorted(best.values(), key=lambda item: (item.offset, item.length, -item.confidence))[:50]
