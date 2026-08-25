"""Conservative cleanup and cross-capture identity rules for OCR player rows."""

from __future__ import annotations

import re
from collections.abc import Mapping
from difflib import SequenceMatcher
from typing import Protocol


class PlayerEvidence(Protocol):
    """The factual fields needed to reconcile two observed player rows."""

    name: str
    positions: str
    ca: str
    pa: str
    attributes: object


def playerNameClean(value: str) -> str:
    """Remove only layout debris that cannot be meaningful name punctuation."""

    cleaned = " ".join(value.split())
    cleaned = re.sub(r"\s*,+\s*", ", ", cleaned)
    cleaned = re.sub(r"\s*'\s*", "'", cleaned)
    cleaned = re.sub(r"\s*-\s*", "-", cleaned)
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    return cleaned.strip(" ,;:")


def playerNameIsUncertain(value: str) -> bool:
    """Flag the characteristic unpunctuated 1–2 letter OCR fragment for review.

    Initials carrying a full stop, hyphenated parts and apostrophe names are retained
    without warning. The fragment is deliberately not removed without corroboration.
    """

    name = playerNameClean(value)
    parts = name.replace(",", " ").split()
    return any(
        token.isalpha()
        and len(token) <= 2
        and "." not in token
        and "-" not in token
        and "'" not in token
        for token in parts
    )


def playerEvidenceMatches(first: PlayerEvidence, second: PlayerEvidence) -> bool:
    """Reconcile names only when similarity is corroborated by stable squad facts."""

    firstName = _nameComparable(first.name)
    secondName = _nameComparable(second.name)
    if not firstName or not secondName:
        return False
    if firstName == secondName:
        return True

    similarity = SequenceMatcher(None, firstName, secondName).ratio()
    fragmentVariant = _withoutShortFragments(first.name) == _withoutShortFragments(second.name)
    facts = _factAgreement(first, second)
    # A likely inserted fragment still needs two independent factual agreements.
    # General fuzzy names require stronger similarity and the same corroboration.
    return facts >= 2 and (fragmentVariant or similarity >= 0.92)


def preferredPlayerName(first: PlayerEvidence, second: PlayerEvidence) -> str:
    """Choose the least suspicious, highest-confidence observed name rendering."""

    candidates = (playerNameClean(first.name), playerNameClean(second.name))
    confidence = (
        float(getattr(first, "confidence", 0.0) or 0.0),
        float(getattr(second, "confidence", 0.0) or 0.0),
    )
    ranked = sorted(
        zip(candidates, confidence, strict=True),
        key=lambda item: (
            playerNameIsUncertain(item[0]),
            -item[1],
            len(item[0]),
        ),
    )
    return ranked[0][0]


def _nameComparable(value: str) -> str:
    return re.sub(r"[^\w]", "", playerNameClean(value).casefold())


def _withoutShortFragments(value: str) -> str:
    tokens = re.findall(r"[^\W_]+", playerNameClean(value).casefold())
    return "".join(token for token in tokens if len(token) > 2)


def _attributeValues(player: PlayerEvidence) -> dict[str, int | None]:
    attributes = player.attributes
    if isinstance(attributes, Mapping):
        return dict(attributes)
    result: dict[str, int | None] = {}
    for item in attributes or ():
        if isinstance(item, tuple) and len(item) == 2:
            result[str(item[0])] = item[1]
        elif hasattr(item, "attributeName"):
            result[str(item.attributeName)] = item.attributeValue
    return result


def _factAgreement(first: PlayerEvidence, second: PlayerEvidence) -> int:
    agreements = 0
    if (
        first.positions.strip()
        and first.positions.strip().casefold() == second.positions.strip().casefold()
    ):
        agreements += 1
    for field in ("ca", "pa"):
        firstValue = getattr(first, field).strip()
        secondValue = getattr(second, field).strip()
        if firstValue and firstValue == secondValue:
            agreements += 1
    firstAttributes = _attributeValues(first)
    secondAttributes = _attributeValues(second)
    overlap = {
        name
        for name in firstAttributes.keys() & secondAttributes.keys()
        if firstAttributes[name] is not None and secondAttributes[name] is not None
    }
    if (
        overlap
        and sum(firstAttributes[name] == secondAttributes[name] for name in overlap) / len(overlap)
        >= 0.8
    ):
        agreements += 1
    return agreements
