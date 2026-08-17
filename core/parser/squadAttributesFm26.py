"""FM26-specific refinements for the squad attributes parser."""

from __future__ import annotations

import re

from fmsat.core.ocr import OcrResult

from .squadAttributes import SquadAttributesParser as _BaseSquadAttributesParser


class SquadAttributesParser(_BaseSquadAttributesParser):
    """Prefer complete multi-fragment FM headers before clipped single fragments."""

    def _attributeHeaderFind(
        self,
        results: list[OcrResult],
        attributeName: str,
        headerY: float,
        tolerance: float,
        minimumX: float,
    ) -> OcrResult | None:
        composite = self._compositeHeaderFind(
            results,
            attributeName,
            headerY,
            tolerance,
            minimumX,
        )
        if composite is not None:
            return composite
        return super()._attributeHeaderFind(
            results,
            attributeName,
            headerY,
            tolerance,
            minimumX,
        )

    def _compositeHeaderFind(
        self,
        results: list[OcrResult],
        attributeName: str,
        headerY: float,
        tolerance: float,
        minimumX: float,
    ) -> OcrResult | None:
        """Join FM headers split by OCR, including ``First`` + ``Touch``."""

        expected = self._tokenNormalize(attributeName)
        candidates = sorted(
            (
                result
                for result in results
                if result.bounds is not None
                and result.center is not None
                and abs(result.center[1] - headerY) <= tolerance
                and result.center[0] > minimumX
            ),
            key=lambda result: result.center[0],
        )
        groups: list[list[OcrResult]] = []
        for width in (2, 3):
            groups.extend(
                candidates[start : start + width]
                for start in range(len(candidates) - width + 1)
            )
        # Paddle can interleave a tiny neighbouring-column fragment between the
        # two words of First Touch. Try every nearby pair as a second pass.
        groups.extend(
            [left, right]
            for index, left in enumerate(candidates)
            for right in candidates[index + 1 :]
            if right.center is not None
            and left.center is not None
            and 0 < right.center[0] - left.center[0] <= 140
        )
        for group in groups:
            tokens = [self._tokenNormalize(result.text) for result in group]
            if any(not token for token in tokens):
                continue
            joined = "".join(tokens)
            if joined != expected and not (
                len(joined) >= 3 and expected.startswith(joined)
            ):
                continue
            left = min(result.bounds[0] for result in group if result.bounds is not None)
            top = min(result.bounds[1] for result in group if result.bounds is not None)
            right = max(result.bounds[2] for result in group if result.bounds is not None)
            bottom = max(result.bounds[3] for result in group if result.bounds is not None)
            confidence = sum(result.confidence for result in group) / len(group)
            return OcrResult(
                " ".join(result.text for result in group),
                confidence,
                (left, top, right, bottom),
            )
        return None

    @staticmethod
    def _playerNameTextClean(value: str) -> str:
        """Apply base name cleanup and remove punctuation introduced at the row edge."""

        cleaned = _BaseSquadAttributesParser._playerNameTextClean(value)
        return re.sub(r"[.,;:]+$", "", cleaned).rstrip()
