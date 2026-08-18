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

        direct = super()._attributeHeaderFind(
            results,
            attributeName,
            headerY,
            tolerance,
            minimumX,
        )
        if direct is not None:
            return direct

        if attributeName == "first_touch":
            return self._firstTouchHeaderInfer(
                results,
                headerY,
                tolerance,
                minimumX,
            )
        if attributeName in {"acceleration", "agility"}:
            return self._physicalHeaderInfer(
                results,
                attributeName,
                headerY,
                tolerance,
                minimumX,
            )
        return None

    def _firstTouchHeaderInfer(
        self,
        results: list[OcrResult],
        headerY: float,
        tolerance: float,
        minimumX: float,
    ) -> OcrResult | None:
        """Infer First Touch between Finishing and Heading when OCR drops its label."""

        finishing = super()._attributeHeaderFind(
            results,
            "finishing",
            headerY,
            tolerance,
            minimumX,
        )
        heading = super()._attributeHeaderFind(
            results,
            "heading",
            headerY,
            tolerance,
            minimumX,
        )
        if (
            finishing is None
            or heading is None
            or finishing.center is None
            or heading.center is None
            or heading.center[0] <= finishing.center[0]
        ):
            return None

        centerX = (finishing.center[0] + heading.center[0]) / 2
        gap = heading.center[0] - finishing.center[0]
        halfWidth = max(4.0, gap * 0.18)
        halfHeight = max(4.0, tolerance * 0.25)
        return OcrResult(
            "First Touch (inferred)",
            min(finishing.confidence, heading.confidence),
            (
                centerX - halfWidth,
                headerY - halfHeight,
                centerX + halfWidth,
                headerY + halfHeight,
            ),
        )

    def _physicalHeaderInfer(
        self,
        results: list[OcrResult],
        attributeName: str,
        headerY: float,
        tolerance: float,
        minimumX: float,
    ) -> OcrResult | None:
        """Infer FM's Acceleration/Agility columns between Technique and Balance."""

        technique = super()._attributeHeaderFind(
            results,
            "technique",
            headerY,
            tolerance,
            minimumX,
        )
        balance = super()._attributeHeaderFind(
            results,
            "balance",
            headerY,
            tolerance,
            minimumX,
        )
        if (
            technique is None
            or balance is None
            or technique.center is None
            or balance.center is None
            or balance.center[0] <= technique.center[0]
        ):
            return None

        gap = balance.center[0] - technique.center[0]
        fraction = 1 / 3 if attributeName == "acceleration" else 2 / 3
        centerX = technique.center[0] + gap * fraction
        halfWidth = max(4.0, gap * 0.10)
        halfHeight = max(4.0, tolerance * 0.25)
        return OcrResult(
            f"{attributeName.replace('_', ' ').title()} (inferred)",
            min(technique.confidence, balance.confidence),
            (
                centerX - halfWidth,
                headerY - halfHeight,
                centerX + halfWidth,
                headerY + halfHeight,
            ),
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
