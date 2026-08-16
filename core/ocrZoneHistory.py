"""Historical OCR-zone geometry and robust drift classification."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable


@dataclass(frozen=True, slots=True)
class OcrZoneGeometry:
    """Normalized OCR-zone geometry within its source screenshot."""

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class OcrZoneDriftResult:
    """Explainable comparison of one geometry observation with its history."""

    state: str
    score: float | None
    historyCount: int
    baseline: OcrZoneGeometry | None
    delta: OcrZoneGeometry | None


class OcrZoneDriftClassifier:
    """Classify OCR geometry using median and median absolute deviation (MAD)."""

    def __init__(
        self,
        minimumHistory: int = 5,
        normalScoreMax: float = 3.5,
        driftingScoreMax: float = 6.0,
        minimumScale: float = 0.002,
    ) -> None:
        self.minimumHistory = minimumHistory
        self.normalScoreMax = normalScoreMax
        self.driftingScoreMax = driftingScoreMax
        self.minimumScale = minimumScale

    def classify(
        self,
        current: OcrZoneGeometry,
        history: Iterable[OcrZoneGeometry],
    ) -> OcrZoneDriftResult:
        """Return normal, drifting, anomalous or unavailable with full deltas."""

        samples = tuple(history)
        if len(samples) < self.minimumHistory:
            return OcrZoneDriftResult("unavailable", None, len(samples), None, None)

        baseline = OcrZoneGeometry(*(
            median(tuple(getattr(item, field) for item in samples))
            for field in ("x", "y", "width", "height")
        ))
        delta = OcrZoneGeometry(
            current.x - baseline.x,
            current.y - baseline.y,
            current.width - baseline.width,
            current.height - baseline.height,
        )
        scores = []
        for field in ("x", "y", "width", "height"):
            values = tuple(getattr(item, field) for item in samples)
            centre = getattr(baseline, field)
            mad = median(tuple(abs(value - centre) for value in values))
            scale = max(1.4826 * mad, self.minimumScale)
            scores.append(abs(getattr(current, field) - centre) / scale)
        score = max(scores)
        state = (
            "normal"
            if score <= self.normalScoreMax
            else "drifting"
            if score <= self.driftingScoreMax
            else "anomalous"
        )
        return OcrZoneDriftResult(state, score, len(samples), baseline, delta)
