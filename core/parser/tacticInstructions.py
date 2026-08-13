"""Selected-only team-instruction extraction from Football Manager screens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from fmsat.core.ocr import OcrEngine, OcrResult

from .tacticModels import TacticalPhase, TacticIssue, TeamInstruction, ValidationState
from .tacticVocabulary import TacticVocabulary


@dataclass(frozen=True, slots=True)
class InstructionExtractResult:
    """Observed selected instructions and unresolved extraction findings."""

    instructions: tuple[TeamInstruction, ...]
    issues: tuple[TacticIssue, ...]


class TacticInstructionExtractor:
    """Read configured instruction cards without persisting unselected values."""

    def __init__(
        self,
        ocr: OcrEngine,
        vocabulary: TacticVocabulary,
        configuration: dict[str, Any],
    ) -> None:
        self.ocr = ocr
        self.vocabulary = vocabulary
        self.configuration = configuration

    def instructionsExtract(
        self,
        image: np.ndarray,
        phase: TacticalPhase,
        sourceImport: str,
    ) -> InstructionExtractResult:
        """Persist only one visually selected, canonical value per category."""

        categories = self.configuration.get("instructionRegions", {}).get(phase.value, {})
        instructions: list[TeamInstruction] = []
        issues: list[TacticIssue] = []
        if not categories:
            return InstructionExtractResult((), (
                TacticIssue(
                    "missingInstructionConfiguration",
                    f"No instruction regions are configured for {phase.value}",
                ),
            ))
        for category, region in categories.items():
            crop = self._regionCrop(image, region)
            if crop.size == 0:
                issues.append(TacticIssue(
                    "emptyInstructionRegion",
                    f"Configured {phase.value}.{category} region is empty",
                ))
                continue
            try:
                results = self.ocr.recognize(crop)
            except Exception as exc:
                issues.append(TacticIssue(
                    "instructionOcrFailed",
                    f"{phase.value}.{category} OCR failed: {exc}",
                ))
                continue
            normalizedResults = [
                (
                    result,
                    self.vocabulary.instructionNormalize(
                        phase.value,
                        category,
                        result.text,
                    ),
                )
                for result in results
            ]
            canonicalResults = [
                result for result, normalized in normalizedResults if normalized.resolved
            ]
            selected = self._selectedResults(crop, canonicalResults)
            if len(selected) != 1:
                unknownSelected = self._selectedResults(
                    crop,
                    [
                        result
                        for result, normalized in normalizedResults
                        if not normalized.resolved
                    ],
                )
                if not selected and len(unknownSelected) == 1:
                    issues.append(TacticIssue(
                        "unknownInstructionValue",
                        f"{phase.value}.{category} selected value is not canonical",
                        unknownSelected[0][0].text,
                    ))
                    continue
                code = (
                    "missingInstructionEvidence"
                    if not selected
                    else "ambiguousInstructionEvidence"
                )
                observed = ", ".join(result.text for result, _ in selected) or None
                issues.append(TacticIssue(
                    code,
                    f"{phase.value}.{category} has {len(selected)} selected values; "
                    "exactly one is required",
                    observed,
                ))
                continue
            result, selectionScore = selected[0]
            normalized = self.vocabulary.instructionNormalize(
                phase.value,
                category,
                result.text,
            )
            if not normalized.resolved:
                issues.append(TacticIssue(
                    "unknownInstructionValue",
                    f"{phase.value}.{category} selected value is not canonical",
                    result.text,
                ))
                continue
            canonical = str(normalized.value)
            confidence = min(result.confidence, selectionScore)
            value: str | bool = canonical
            if canonical.casefold() in {"true", "false"}:
                value = canonical.casefold() == "true"
            instructions.append(TeamInstruction(
                phase=phase,
                category=category,
                value=value,
                displayValue=result.text.strip(),
                confidence=confidence,
                sourceImport=sourceImport,
                validationState=ValidationState.EXTRACTED,
            ))
        return InstructionExtractResult(tuple(instructions), tuple(issues))

    def _selectedResults(
        self,
        crop: np.ndarray,
        results: list[OcrResult],
    ) -> list[tuple[OcrResult, float]]:
        candidates: list[tuple[OcrResult, float]] = []
        minimumScore = float(
            self.configuration.get("selection", {}).get("minimumScore", 0.25)
        )
        for result in results:
            score = self._selectionScore(crop, result)
            if score >= minimumScore:
                candidates.append((result, score))

        if len(candidates) <= 1:
            return candidates

        # Unselected FM options can still contain small coloured controls. A
        # selected option colours most of its row, so accept the strongest row
        # only when it is visually distinct. Similar scores remain ambiguous.
        candidates.sort(key=lambda item: item[1], reverse=True)
        minimumMargin = float(
            self.configuration.get("selection", {}).get("minimumMargin", 0.12)
        )
        if candidates[0][1] - candidates[1][1] >= minimumMargin:
            return [candidates[0]]
        return candidates

    def _selectionScore(self, crop: np.ndarray, result: OcrResult) -> float:
        """Measure coloured selected-state evidence behind an OCR result."""

        if result.bounds is None:
            # A region containing exactly one recognized value is still usable
            # for OCR engines without geometry; ambiguity is handled by the caller.
            return result.confidence
        height, width = crop.shape[:2]
        _, top, _, bottom = result.bounds
        padding = int(self.configuration.get("selection", {}).get("padding", 5))
        # Sample the complete horizontal option row rather than the text box.
        # Text antialiasing and icons can be saturated even when an option is
        # not selected; the selected background is visible across the row.
        x1, y1 = 0, max(0, int(top) - padding)
        x2, y2 = width, min(height, int(bottom) + padding)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        hsv = cv2.cvtColor(crop[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
        minimumSaturation = int(
            self.configuration.get("selection", {}).get("minimumSaturation", 45)
        )
        selectedPixels = hsv[:, :, 1] >= minimumSaturation
        return float(np.count_nonzero(selectedPixels) / selectedPixels.size)

    @staticmethod
    def _regionCrop(image: np.ndarray, region: dict[str, float]) -> np.ndarray:
        height, width = image.shape[:2]
        left, top = int(float(region["x"]) * width), int(float(region["y"]) * height)
        right = int((float(region["x"]) + float(region["width"])) * width)
        bottom = int((float(region["y"]) + float(region["height"])) * height)
        return image[max(0, top):min(height, bottom), max(0, left):min(width, right)]
