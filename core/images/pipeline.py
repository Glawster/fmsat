"""Composable OpenCV preprocessing stages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


class ImageProcessingError(RuntimeError):
    """Raised when a screenshot cannot be loaded or transformed."""


def _cv2() -> Any:
    try:
        import cv2
    except ImportError as exc:
        raise ImageProcessingError(
            "OpenCV is not installed. Install the project dependencies first."
        ) from exc
    return cv2


def imageLoad(path: Path) -> np.ndarray:
    """Load a PNG or JPEG screenshot as a BGR image."""

    if not path.is_file():
        raise ImageProcessingError(f"Screenshot does not exist: {path}")
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise ImageProcessingError("Only PNG and JPEG screenshots are supported")
    image = _cv2().imread(str(path), _cv2().IMREAD_COLOR)
    if image is None:
        raise ImageProcessingError(f"Unable to decode screenshot: {path}")
    return image


@dataclass(frozen=True, slots=True)
class PreprocessingOptions:
    """Switches and parameters for the screenshot preprocessing pipeline."""

    cropBorders: bool = True
    borderFraction: float = 0.005
    increaseContrast: bool = True
    contrastClipLimit: float = 2.0
    deskew: bool = False
    denoise: bool = True
    sharpen: bool = True
    threshold: bool = False

    @classmethod
    def fromMapping(cls, values: dict[str, Any]) -> PreprocessingOptions:
        """Build options from YAML values while retaining safe defaults."""

        defaults = cls()
        yamlNames = {
            "cropBorders": "crop_borders",
            "borderFraction": "border_fraction",
            "increaseContrast": "increase_contrast",
            "contrastClipLimit": "contrast_clip_limit",
            "deskew": "deskew",
            "denoise": "denoise",
            "sharpen": "sharpen",
            "threshold": "threshold",
        }
        return cls(
            **{
                fieldName: values.get(yamlName, getattr(defaults, fieldName))
                for fieldName, yamlName in yamlNames.items()
            }
        )


class ImagePreprocessor:
    """Runs small, independently callable preprocessing stages."""

    def __init__(self, options: PreprocessingOptions | None = None) -> None:
        self.options = options or PreprocessingOptions()

    def process(self, image: np.ndarray) -> np.ndarray:
        """Apply enabled stages in a stable order."""

        if image is None or image.size == 0:
            raise ImageProcessingError("Cannot preprocess an empty image")
        result = self.rgbConvert(image)
        if self.options.cropBorders:
            result = self.bordersCrop(result)
        if self.options.increaseContrast:
            result = self.contrastIncrease(result)
        if self.options.deskew:
            result = self.deskew(result)
        if self.options.denoise:
            result = self.denoise(result)
        if self.options.sharpen:
            result = self.textSharpen(result)
        if self.options.threshold:
            result = self.threshold(result)
        return result

    def bordersCrop(self, image: np.ndarray) -> np.ndarray:
        """Remove a configurable fraction from every edge."""

        height, width = image.shape[:2]
        xMargin = min(int(width * self.options.borderFraction), max(width // 4, 0))
        yMargin = min(int(height * self.options.borderFraction), max(height // 4, 0))
        if not xMargin and not yMargin:
            return image.copy()
        return image[yMargin : height - yMargin, xMargin : width - xMargin].copy()

    def contrastIncrease(self, image: np.ndarray) -> np.ndarray:
        """Increase local luminance contrast without distorting colour heavily."""

        cv2 = _cv2()
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        lightness, channelA, channelB = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=self.options.contrastClipLimit, tileGridSize=(8, 8))
        enhanced = clahe.apply(lightness)
        return cv2.cvtColor(cv2.merge((enhanced, channelA, channelB)), cv2.COLOR_LAB2RGB)

    def denoise(self, image: np.ndarray) -> np.ndarray:
        """Remove light UI compression noise."""

        return _cv2().fastNlMeansDenoisingColored(image, None, 3, 3, 7, 21)

    def deskew(self, image: np.ndarray) -> np.ndarray:
        """Correct the dominant small text-line rotation."""

        cv2 = _cv2()
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        points = np.column_stack(np.where(gray < np.percentile(gray, 35)))
        if len(points) < 10:
            return image.copy()
        angle = cv2.minAreaRect(points.astype(np.float32))[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) > 10:
            return image.copy()
        height, width = image.shape[:2]
        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
        return cv2.warpAffine(
            image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

    def rgbConvert(self, image: np.ndarray) -> np.ndarray:
        """Convert OpenCV BGR input to RGB."""

        if image.ndim == 2:
            return _cv2().cvtColor(image, _cv2().COLOR_GRAY2RGB)
        return _cv2().cvtColor(image, _cv2().COLOR_BGR2RGB)

    def textSharpen(self, image: np.ndarray) -> np.ndarray:
        """Apply an unsharp mask suitable for UI text."""

        cv2 = _cv2()
        blurred = cv2.GaussianBlur(image, (0, 0), 1.0)
        return cv2.addWeighted(image, 1.5, blurred, -0.5, 0)

    def threshold(self, image: np.ndarray) -> np.ndarray:
        """Create a three-channel adaptive binary image."""

        cv2 = _cv2()
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 8
        )
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
