"""Central application logging configuration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def loggingConfigure(logDirectory: Path) -> Path:
    """Configure console and rotating file logging once."""

    logDirectory.mkdir(parents=True, exist_ok=True)
    logPath = logDirectory / "application.log"
    root = logging.getLogger()
    if any(getattr(handler, "_fmsatHandler", False) for handler in root.handlers):
        return logPath
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fileHandler = RotatingFileHandler(
        logPath, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fileHandler.setFormatter(formatter)
    fileHandler._fmsatHandler = True  # type: ignore[attr-defined]
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(formatter)
    consoleHandler._fmsatHandler = True  # type: ignore[attr-defined]
    root.addHandler(fileHandler)
    root.addHandler(consoleHandler)
    return logPath
