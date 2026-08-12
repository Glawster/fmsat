"""Heuristics for finding repeated binary structures."""

from __future__ import annotations

from collections import Counter

from fmsat.fmf.structures import RepeatedStructureCandidate


def structuresRepeated(
    data: bytes,
    *,
    minRecordLength: int = 4,
    maxRecordLength: int = 64,
    minCount: int = 3,
) -> tuple[RepeatedStructureCandidate, ...]:
    """Find repeated chunks that may indicate arrays or fixed-width records."""

    candidates: list[RepeatedStructureCandidate] = []
    for recordLength in range(minRecordLength, maxRecordLength + 1):
        for offset in range(0, min(recordLength, len(data))):
            chunks = [
                data[index : index + recordLength]
                for index in range(offset, len(data) - recordLength + 1, recordLength)
            ]
            counts = Counter(chunks)
            if not counts:
                continue
            _chunk, count = counts.most_common(1)[0]
            if count >= minCount:
                confidence = min(0.2 + (count / max(1, len(chunks))) * 0.8, 0.95)
                candidates.append(
                    RepeatedStructureCandidate(
                        offset=offset,
                        recordLength=recordLength,
                        count=count,
                        confidence=confidence,
                        reason="same fixed-width chunk appears repeatedly",
                    )
                )
    return tuple(sorted(candidates, key=lambda item: (-item.confidence, item.recordLength))[:50])
