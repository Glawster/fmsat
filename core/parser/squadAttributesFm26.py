"""FM26-specific refinements for the squad attributes parser."""

from __future__ import annotations

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
        """Join adjacent OCR fragments such as ``First`` + ``Touch``."""

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
        for width in (2, 3):
            for start in range(len(candidates) - width + 1):
                group = candidates[start : start + width]
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
