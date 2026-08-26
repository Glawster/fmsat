"""Managed local storage for imported screenshots."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
from fmsat.core.logUtils import getLogger

from .images.pipeline import ImageProcessingError, _cv2

logger = getLogger()


class ScreenshotStoreError(RuntimeError):
    """Raised when a managed screenshot cannot be stored or removed."""


class ScreenshotStore:
    """Save and remove screenshots within one validated managed directory."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory.resolve()

    def captureSave(
        self,
        image: np.ndarray,
        ownerType: str,
        ownerName: str,
        screenType: str,
        *,
        capturedAt: datetime | None = None,
        identifier: str | None = None,
    ) -> Path:
        """Save an original screenshot as a uniquely named PNG."""

        if image is None or image.size == 0:
            raise ScreenshotStoreError("Cannot store an empty screenshot")
        timestamp = (capturedAt or datetime.now()).strftime("%Y%m%d-%H%M%S")
        suffix = self._slug(identifier or uuid4().hex[:8])
        filename = "_".join(
            (
                timestamp,
                f"{self._slug(ownerType)}-{self._slug(ownerName)}",
                self._slug(screenType),
                suffix,
            )
        )
        path = self.directory / f"{filename}.png"
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            encoded, content = _cv2().imencode(".png", image)
            if not encoded:
                raise ScreenshotStoreError("Unable to encode screenshot as PNG")
            with path.open("xb") as stream:
                stream.write(content.tobytes())
        except (OSError, ImageProcessingError) as exc:
            logger.exception("screenshot save failed path=%s", path)
            raise ScreenshotStoreError(f"Unable to store screenshot: {exc}") from exc
        logger.action(
            f"screenshot saved path={path} ownerType={ownerType} "
            f"ownerName={ownerName!r} screenType={screenType}"
        )
        return path

    def capturesRemove(self, paths: list[str | Path]) -> list[Path]:
        """Remove managed screenshots and return paths which could not be removed."""

        failures: list[Path] = []
        for value in paths:
            path = Path(value).resolve()
            # Legacy imports stored values such as ``clipboard`` rather than a
            # retained image path. There is no file cleanup to perform when the
            # referenced path does not exist.
            if not path.exists():
                continue
            if path.parent != self.directory:
                logger.warning(f"screenshot removal refused unmanaged path={path}")
                failures.append(path)
                continue
            try:
                path.unlink(missing_ok=True)
                logger.action(f"screenshot removed path={path}")
            except OSError:
                logger.exception("screenshot removal failed path=%s", path)
                failures.append(path)
        return failures

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
        return slug or "unnamed"
