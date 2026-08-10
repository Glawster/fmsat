"""Compression discovery helpers."""

from __future__ import annotations

import gzip
import lzma
import zlib
from collections.abc import Callable

from fmsat.core.logUtils import getLogger

from fmsat.fmf.structures import CompressionAttempt

LOGGER = getLogger()

Decompressor = Callable[[bytes], bytes]


def _zlib(data: bytes) -> bytes:
    return zlib.decompress(data)


def _gzip(data: bytes) -> bytes:
    return gzip.decompress(data)


def _lzma(data: bytes) -> bytes:
    return lzma.decompress(data)


def _deflate(data: bytes) -> bytes:
    return zlib.decompress(data, -zlib.MAX_WBITS)


def _optionalLz4(data: bytes) -> bytes:
    import lz4.frame  # type: ignore[import-not-found]

    return lz4.frame.decompress(data)


def _optionalZstd(data: bytes) -> bytes:
    import zstandard  # type: ignore[import-not-found]

    return zstandard.ZstdDecompressor().decompress(data)


def _decompressors() -> tuple[tuple[str, Decompressor], ...]:
    return (
        ("zlib", _zlib),
        ("gzip", _gzip),
        ("lzma", _lzma),
        ("deflate", _deflate),
        ("lz4", _optionalLz4),
        ("zstd", _optionalZstd),
    )


def compressionProbe(
    data: bytes,
    *,
    offsets: tuple[int, ...] = (0,),
    maxLength: int | None = None,
) -> tuple[CompressionAttempt, ...]:
    """Try known compression algorithms at selected offsets."""

    attempts: list[CompressionAttempt] = []
    for offset in offsets:
        block = data[offset : offset + maxLength if maxLength else None]
        for algorithm, decompressor in _decompressors():
            try:
                output = decompressor(block)
            except Exception as exc:  # noqa: BLE001 - this is an exploratory probe.
                attempts.append(
                    CompressionAttempt(
                        algorithm=algorithm,
                        offset=offset,
                        inputLength=len(block),
                        success=False,
                        error=type(exc).__name__,
                    )
                )
                continue
            LOGGER.info(
                "compression probe succeeded: algorithm=%s offset=%d input=%d output=%d",
                algorithm,
                offset,
                len(block),
                len(output),
            )
            attempts.append(
                CompressionAttempt(
                    algorithm=algorithm,
                    offset=offset,
                    inputLength=len(block),
                    success=True,
                    outputLength=len(output),
                )
            )
    return tuple(attempts)
