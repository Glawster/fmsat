"""Shared cleanup for text extracted by OCR."""

from __future__ import annotations


def ocrTextClean(value: str) -> str:
    """Remove whitespace and punctuation that cannot begin an extracted field."""

    return value.lstrip(" .-").rstrip()
