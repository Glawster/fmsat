"""Binary reading primitives used by the reverse engineering tools."""

from __future__ import annotations

import struct
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum


class Endian(str, Enum):  # noqa: UP042 - retains compatibility with existing Python 3.10 tools
    """Supported byte orders."""

    LITTLE = "<"
    BIG = ">"


@dataclass(frozen=True)
class Bookmark:
    """Named offset saved during binary exploration."""

    name: str
    offset: int


class BinaryReader:
    """Convenience wrapper around bytes with typed reads and offset bookmarks."""

    def __init__(self, data: bytes, endian: Endian = Endian.LITTLE) -> None:
        self._data = data
        self._offset = 0
        self.endian = endian
        self._bookmarks: dict[str, Bookmark] = {}

    @property
    def data(self) -> bytes:
        return self._data

    @property
    def offset(self) -> int:
        return self._offset

    @property
    def remaining(self) -> int:
        return len(self._data) - self._offset

    @property
    def bookmarks(self) -> tuple[Bookmark, ...]:
        return tuple(self._bookmarks.values())

    def seek(self, offset: int) -> None:
        if offset < 0 or offset > len(self._data):
            raise ValueError(f"offset {offset} outside buffer length {len(self._data)}")
        self._offset = offset

    def skip(self, length: int) -> None:
        self.seek(self._offset + length)

    def tell(self) -> int:
        return self._offset

    def bookmark(self, name: str) -> Bookmark:
        mark = Bookmark(name=name, offset=self._offset)
        self._bookmarks[name] = mark
        return mark

    @contextmanager
    def at(self, offset: int) -> Iterator[None]:
        current = self._offset
        self.seek(offset)
        try:
            yield
        finally:
            self.seek(current)

    def bytesRead(self, length: int) -> bytes:
        if length < 0:
            raise ValueError("length must be non-negative")
        end = self._offset + length
        if end > len(self._data):
            raise EOFError("not enough bytes remaining")
        chunk = self._data[self._offset : end]
        self._offset = end
        return chunk

    def bytesPeek(self, length: int) -> bytes:
        with self.at(self._offset):
            return self.bytesRead(length)

    def _unpack(self, fmt: str) -> int | float:
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.bytesRead(size))[0]

    def uint8(self) -> int:
        return int(self._unpack("B"))

    def int8(self) -> int:
        return int(self._unpack("b"))

    def uint16(self, endian: Endian | None = None) -> int:
        return int(self._unpack(f"{endian or self.endian}H"))

    def int16(self, endian: Endian | None = None) -> int:
        return int(self._unpack(f"{endian or self.endian}h"))

    def uint32(self, endian: Endian | None = None) -> int:
        return int(self._unpack(f"{endian or self.endian}I"))

    def int32(self, endian: Endian | None = None) -> int:
        return int(self._unpack(f"{endian or self.endian}i"))

    def uint64(self, endian: Endian | None = None) -> int:
        return int(self._unpack(f"{endian or self.endian}Q"))

    def int64(self, endian: Endian | None = None) -> int:
        return int(self._unpack(f"{endian or self.endian}q"))

    def float32(self, endian: Endian | None = None) -> float:
        return float(self._unpack(f"{endian or self.endian}f"))

    def float64(self, endian: Endian | None = None) -> float:
        return float(self._unpack(f"{endian or self.endian}d"))

    def varuint(self) -> int:
        """Read a base-128 little-endian variable-length unsigned integer."""

        result = 0
        shift = 0
        while True:
            byte = self.uint8()
            result |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return result
            shift += 7
            if shift > 63:
                raise ValueError("variable-length integer is too large")

    def varint(self) -> int:
        """Read a ZigZag-encoded signed variable-length integer."""

        value = self.varuint()
        return (value >> 1) ^ -(value & 1)
