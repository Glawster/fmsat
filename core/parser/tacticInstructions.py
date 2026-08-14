"""Selected-only team-instruction extraction from Football Manager screens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from fmsat.core.logUtils import getLogger
from fmsat.core.ocr import OcrEngine, OcrResult

from .tacticFormation import TacticFormationExtractor
from .tacticLayout import TacticLayoutAnchor
from .tacticModels import TacticalPhase, TacticIssue, TeamInstruction, ValidationState
from .tacticVocabulary import TacticVocabulary

logger = getLogger()


@dataclass(frozen=True, slots=True)
class InstructionExtractResult:
    """Observed selected instructions and unresolved extraction findings."""

    instructions: tuple[TeamInstruction, ...]
    issues: tuple[TacticIssue, ...]
    diagnosticImage: np.ndarray | None = None


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
        self.layoutAnchor = TacticLayoutAnchor(ocr, configuration)

    def instructionsExtract(
        self,
        image: np.ndarray,
        phase: TacticalPhase,
        sourceImport: str,
    ) -> InstructionExtractResult:
        """Persist only one visually selected, canonical value per category."""

        layout = self.layoutAnchor.referenceExtract(image, phase)
        image = layout.image
        diagnostic = image.copy()
        TacticFormationExtractor._diagnosticTitle(
            diagnostic, f"{phase.value.upper()} OCR REFERENCE", layout.anchored
        )
        anchorSettings = self.configuration.get("anchors", {})
        if (
            self.configuration.get("anchors", {}).get("enabled", False)
            and not layout.anchored
        ):
            focus = anchorSettings.get("instructionBreadcrumbRegion", {})
            breadcrumbRegion = {
                "x": float(focus.get("x", 0.15)),
                "y": float(focus.get("y", 0.12)),
                "width": float(focus.get("width", 0.70)),
                "height": float(focus.get("height", 0.24)),
            }
            TacticFormationExtractor._diagnosticBox(
                diagnostic,
                self._regionBounds(image, breadcrumbRegion),
                "focused breadcrumb OCR retry",
                (0, 215, 255),
                3,
            )
            return InstructionExtractResult((), layout.issues, diagnostic)
        tabBand = {
            "x": 0.0,
            "y": float(anchorSettings.get("tabBandYMin", 0.08)),
            "width": 1.0,
            "height": float(anchorSettings.get("tabBandYMax", 0.20))
            - float(anchorSettings.get("tabBandYMin", 0.08)),
        }
        TacticFormationExtractor._diagnosticBox(
            diagnostic,
            self._regionBounds(image, tabBand),
            "active tab search: "
            f"{layout.detectedPhase.value if layout.detectedPhase else 'unresolved'}",
            (255, 255, 0),
            2,
        )
        referenceName = (
            "instructionPanelRegions"
            if self.configuration.get("anchors", {}).get("enabled", False)
            and layout.anchored
            else "instructionRegions"
        )
        categories = self.configuration.get(referenceName, {}).get(phase.value, {})
        instructions: list[TeamInstruction] = []
        issues: list[TacticIssue] = list(layout.issues)
        if not categories:
            return InstructionExtractResult((), (
                TacticIssue(
                    "missingInstructionConfiguration",
                    f"No instruction regions are configured for {phase.value}",
                ),
            ), diagnostic)
        for category, region in categories.items():
            logger.doing(f"extracting {phase.value}.{category} instruction")
            bounds = self._regionBounds(image, region)
            TacticFormationExtractor._diagnosticBox(
                diagnostic, bounds, category, (0, 215, 255), 2
            )
            crop = self._regionCrop(image, region)
            if crop.size == 0:
                issues.append(TacticIssue(
                    "emptyInstructionRegion",
                    f"Configured {phase.value}.{category} region is empty",
                ))
                logger.info(f"{phase.value}.{category} crop is empty")
                continue
            try:
                results = self.ocr.recognize(crop)
            except Exception as exc:
                issues.append(TacticIssue(
                    "instructionOcrFailed",
                    f"{phase.value}.{category} OCR failed: {exc}",
                ))
                logger.exception(f"{phase.value}.{category} instruction OCR failed")
                continue
            results = self._valueRetry(crop, phase, category, results)
            logger.value(f"{phase.value}.{category} OCR values", len(results))
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
            selectionMode = str(
                self.configuration.get("selection", {}).get("mode", "visualRow")
            )
            selected = (
                [(result, result.confidence) for result in canonicalResults]
                if selectionMode == "displayedValue"
                else self._selectedResults(crop, canonicalResults)
            )
            logger.info(
                f"{phase.value}.{category} canonical candidates: "
                f"{', '.join(result.text for result in canonicalResults) or 'none'}"
            )
            if len(selected) != 1:
                unknownResults = [
                    result
                    for result, normalized in normalizedResults
                    if not normalized.resolved
                ]
                unknownSelected = (
                    [(result, result.confidence) for result in unknownResults]
                    if selectionMode == "displayedValue"
                    else self._selectedResults(crop, unknownResults)
                )
                if not selected and len(unknownSelected) == 1:
                    issues.append(TacticIssue(
                        "unknownInstructionValue",
                        f"{phase.value}.{category} selected value is not canonical",
                        unknownSelected[0][0].text,
                    ))
                    logger.info(
                        f"{phase.value}.{category} selected unknown value: "
                        f"{unknownSelected[0][0].text}"
                    )
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
                logger.info(
                    f"{phase.value}.{category} unresolved selected values: "
                    f"{observed or 'none'}"
                )
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
            logger.info(
                f"{phase.value}.{category} selected value: {canonical} "
                f"(confidence {confidence:.3f})"
            )
        return InstructionExtractResult(tuple(instructions), tuple(issues), diagnostic)

    def _valueRetry(
        self,
        crop: np.ndarray,
        phase: TacticalPhase,
        category: str,
        results: list[OcrResult],
    ) -> list[OcrResult]:
        """Retry the lower card value at higher resolution when it was missed."""

        if any(
            self.vocabulary.instructionNormalize(phase.value, category, result.text).resolved
            for result in results
        ):
            return results
        height = crop.shape[0]
        valueCrop = crop[int(height * 0.55):, :]
        if valueCrop.size == 0:
            return results
        enlarged = cv2.resize(
            valueCrop,
            None,
            fx=3.0,
            fy=3.0,
            interpolation=cv2.INTER_CUBIC,
        )
        try:
            retry = self.ocr.recognize(enlarged)
        except Exception:
            logger.exception(f"{phase.value}.{category} focused value OCR retry failed")
            return results
        logger.value(f"{phase.value}.{category} focused OCR values", len(retry))
        return retry or results

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
            logger.info(f"selection score for {result.text!r}: {score:.3f}")
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
        left, top, right, bottom = TacticInstructionExtractor._regionBounds(
            image, region
        )
        height, width = image.shape[:2]
        return image[max(0, top):min(height, bottom), max(0, left):min(width, right)]

    @staticmethod
    def _regionBounds(
        image: np.ndarray, region: dict[str, float]
    ) -> tuple[int, int, int, int]:
        height, width = image.shape[:2]
        left, top = int(float(region["x"]) * width), int(float(region["y"]) * height)
        right = int((float(region["x"]) + float(region["width"])) * width)
        bottom = int((float(region["y"]) + float(region["height"])) * height)
        return left, top, right, bottom
