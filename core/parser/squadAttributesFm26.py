"""FM26-specific refinements for the squad attributes parser."""

from __future__ import annotations

import re
from statistics import median

from fmsat.core.ocr import OcrResult

from .squadAttributes import SquadAttributesParser as _BaseSquadAttributesParser


class SquadAttributesParser(_BaseSquadAttributesParser):
    """Prefer complete multi-fragment FM headers before clipped single fragments."""

    _goalkeeperAttributes = (
        "aerial_reach",
        "communication",
        "command_of_area",
        "eccentricity",
        "handling",
        "kicking",
        "one_on_ones",
        "punching",
        "reflexes",
        "rushing_out",
        "throwing",
    )

    def _headerFind(
        self,
        results: list[OcrResult],
        expected: str,
    ) -> OcrResult | None:
        """Recover FM's narrow CA heading from row geometry when OCR drops it."""

        direct = super()._headerFind(results, expected)
        if direct is not None or expected != "ca":
            return direct

        position = super()._headerFind(results, "position")
        pa = super()._headerFind(results, "pa")
        if (
            position is None
            or pa is None
            or position.center is None
            or pa.center is None
            or pa.center[0] <= position.center[0]
        ):
            return None

        numericXs = [
            result.center[0]
            for result in results
            if result.center is not None
            and result.center[1] > pa.center[1] + 8
            and position.center[0] < result.center[0] < pa.center[0]
            and re.fullmatch(r"\d{2,3}", result.text.strip()) is not None
        ]
        if not numericXs:
            return None

        centerX = float(median(numericXs))
        halfWidth = max(5.0, (pa.center[0] - centerX) * 0.20)
        halfHeight = 6.0
        return OcrResult(
            "CA (inferred)",
            pa.confidence,
            (
                centerX - halfWidth,
                pa.center[1] - halfHeight,
                centerX + halfWidth,
                pa.center[1] + halfHeight,
            ),
        )

    def _attributeHeaderFind(
        self,
        results: list[OcrResult],
        attributeName: str,
        headerY: float,
        tolerance: float,
        minimumX: float,
    ) -> OcrResult | None:
        goalkeeper = self._goalkeeperHeaderInfer(
            results,
            attributeName,
            headerY,
            tolerance,
            minimumX,
        )
        if goalkeeper is not None:
            return goalkeeper

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
        if attributeName == "natural_fitness":
            return self._naturalFitnessHeaderInfer(
                results,
                headerY,
                tolerance,
                minimumX,
            )
        return None

    def _goalkeeperHeaderInfer(
        self,
        results: list[OcrResult],
        attributeName: str,
        headerY: float,
        tolerance: float,
        minimumX: float,
    ) -> OcrResult | None:
        """Use stable FM goalkeeper-column spacing when the screen exposes both anchors."""

        if attributeName not in self._goalkeeperAttributes:
            return None
        aerial = super()._attributeHeaderFind(
            results,
            "aerial_reach",
            headerY,
            tolerance,
            minimumX,
        )
        reflexes = super()._attributeHeaderFind(
            results,
            "reflexes",
            headerY,
            tolerance,
            minimumX,
        )
        if (
            aerial is None
            or reflexes is None
            or aerial.center is None
            or reflexes.center is None
            or reflexes.center[0] <= aerial.center[0]
        ):
            return None

        reflexIndex = self._goalkeeperAttributes.index("reflexes")
        attributeIndex = self._goalkeeperAttributes.index(attributeName)
        step = (reflexes.center[0] - aerial.center[0]) / reflexIndex
        centerX = aerial.center[0] + attributeIndex * step
        halfWidth = max(4.0, step * 0.20)
        halfHeight = max(4.0, tolerance * 0.25)
        return OcrResult(
            f"{attributeName.replace('_', ' ').title()} (inferred)",
            min(aerial.confidence, reflexes.confidence),
            (
                centerX - halfWidth,
                headerY - halfHeight,
                centerX + halfWidth,
                headerY + halfHeight,
            ),
        )

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

    def _naturalFitnessHeaderInfer(
        self,
        results: list[OcrResult],
        headerY: float,
        tolerance: float,
        minimumX: float,
    ) -> OcrResult | None:
        """Infer Natural Fitness between Jumping Reach and FM's visible Long Shots header."""

        jumping = super()._attributeHeaderFind(
            results,
            "jumping_reach",
            headerY,
            tolerance,
            minimumX,
        )
        longShots = super()._attributeHeaderFind(
            results,
            "long_shots",
            headerY,
            tolerance,
            minimumX,
        )
        if (
            jumping is None
            or longShots is None
            or jumping.center is None
            or longShots.center is None
            or longShots.center[0] <= jumping.center[0]
        ):
            return None

        centerX = (jumping.center[0] + longShots.center[0]) / 2
        gap = longShots.center[0] - jumping.center[0]
        halfWidth = max(4.0, gap * 0.18)
        halfHeight = max(4.0, tolerance * 0.25)
        return OcrResult(
            "Natural Fitness (inferred)",
            min(jumping.confidence, longShots.confidence),
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
                candidates[start : start + width] for start in range(len(candidates) - width + 1)
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
            if joined != expected and not (len(joined) >= 3 and expected.startswith(joined)):
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
        """Apply base cleanup and collapse duplicate fragments from overlapping OCR strips."""

        cleaned = _BaseSquadAttributesParser._playerNameTextClean(value)
        cleaned = re.sub(r"^[A-Z](?=[A-Z][a-z]{2})", "", cleaned)
        cleaned = re.sub(r"[.,;:]+$", "", cleaned).rstrip()
        words = cleaned.split()
        if len(words) >= 4:
            for index in range(1, len(words)):
                if words[index].casefold() == words[0].casefold():
                    return " ".join(words[:index])
        return cleaned
