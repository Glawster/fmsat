"""Differential analysis for controlled FMF experiments."""

from __future__ import annotations

from itertools import zip_longest as zipLongest
from pathlib import Path

from fmsat.structures import Change, ChangeGroup


def bytesChanged(old: bytes, new: bytes) -> tuple[Change, ...]:
    changes: list[Change] = []
    sentinel = object()
    for offset, (oldByte, newByte) in enumerate(zipLongest(old, new, fillvalue=sentinel)):
        if oldByte == newByte:
            continue
        changes.append(
            Change(
                offset=offset,
                old=None if oldByte is sentinel else int(oldByte),
                new=None if newByte is sentinel else int(newByte),
            )
        )
    return tuple(changes)


def changesGroup(changes: tuple[Change, ...], *, maxGap: int = 8) -> tuple[ChangeGroup, ...]:
    if not changes:
        return ()
    groups: list[ChangeGroup] = []
    current = [changes[0]]
    for change in changes[1:]:
        if change.offset - current[-1].offset <= maxGap:
            current.append(change)
        else:
            groups.append(_groupMake(current))
            current = [change]
    groups.append(_groupMake(current))
    return tuple(groups)


def filesDiff(oldPath: str | Path, newPath: str | Path) -> tuple[ChangeGroup, ...]:
    old = Path(oldPath).read_bytes()
    new = Path(newPath).read_bytes()
    return changesGroup(bytesChanged(old, new))


def _groupMake(changes: list[Change]) -> ChangeGroup:
    span = changes[-1].offset - changes[0].offset + 1
    if len(changes) == span:
        likely = "contiguous byte range"
    elif len(changes) <= 4:
        likely = "small scalar field or checksum ripple"
    else:
        likely = "clustered structure or compressed/checksummed payload"
    return ChangeGroup(
        start=changes[0].offset,
        end=changes[-1].offset,
        changes=tuple(changes),
        likelyStructure=likely,
    )
