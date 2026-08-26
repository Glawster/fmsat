"""Application logging utilities.

Canonical source:
    Glawster/organiseMyProjects

This file may be a local deployment copy.
Keep behavioural changes synchronized with the canonical implementation.
"""

from __future__ import annotations

import datetime
import logging
import textwrap
from logging import getLogger as _getLogger
from pathlib import Path
from typing import Any, MutableMapping, Optional, Sequence

# logging guidelines:
# all messages in lowercase
# "doing something..." - major action being taken
# "...something done" - above action completed
# "...message" - general update, doing this, transitory information
# "...message: value" - display some information
# ERROR messages should be in Sentence Case.

_initialized_log_files: set[str] = set()

_DRY_RUN_PREFIX = "[] "

thisApplication: str | None = None
_applicationLogDir: Path | None = None


class _OrganiseLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter providing semantic log methods with optional dry-run prefixing."""

    def __init__(self, logger: logging.Logger, dryRun: bool = False):
        super().__init__(logger, {})
        self._dryRun = dryRun
        self._prefix = _DRY_RUN_PREFIX if dryRun else ""

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """Pass through non-semantic calls (warning, error, debug) unchanged."""
        return msg, kwargs

    def info(self, message: str, *args, **kwargs) -> None:
        """Log general information: '...message'.
        Also used where we want to log a complex string containing variables and the format provided by logger.value would not work
        """
        self.logger.info(f"...{message}", *args, **kwargs)

    def multiline(self, lines: str | Sequence[str]) -> None:
        """Log multiline information with three-space indentation after line one.
        Single-line input logs as standard info. Empty input logs as "...".
        """
        if isinstance(lines, str):
            messageLines = lines.splitlines() if lines else []
        else:
            messageLines = list(lines)

        if not messageLines:
            self.logger.info("...")
            return

        firstLine = messageLines[0]
        if len(messageLines) == 1:
            self.logger.info(f"...{firstLine}")
            return

        indentedLines = "\n".join(f"   {line}" for line in messageLines[1:])
        self.logger.info(f"...{firstLine}\n{indentedLines}")

    def value(self, message: str, variable) -> None:
        """Log a name-value pair: '...message: variable'.
        This is the standard format we want to use for variables, that is
        '...variable name: variable value'."""
        self.logger.info(f"...{message}: {variable}")

    def doing(self, message: str, dryRunMessage: Optional[str] = None) -> None:
        """Log a major action being taken, with dry-run awareness."""
        selectedMessage = (
            dryRunMessage if self._dryRun and dryRunMessage is not None else message
        )
        self.logger.info(f"{self._prefix}{selectedMessage}...")

    def done(self, message: str, dryRunMessage: Optional[str] = None) -> None:
        """Log a completed action, with dry-run awareness."""
        selectedMessage = (
            dryRunMessage if self._dryRun and dryRunMessage is not None else message
        )
        self.logger.info(f"...{self._prefix}{selectedMessage}")

    def action(
        self,
        message: str,
        *args,
        dryRunMessage: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log a dry-run-aware action: '...{prefix}message'."""
        selectedMessage = (
            dryRunMessage if self._dryRun and dryRunMessage is not None else message
        )
        self.logger.info(f"...{self._prefix}{selectedMessage}", *args, **kwargs)


def setApplication(name: str, logDir: Optional[Path] = None) -> None:
    """Set the active application context for subsequent getLogger() calls."""
    global thisApplication, _applicationLogDir

    cleanedName = name.strip()
    if not cleanedName:
        raise ValueError("Application name must not be empty.")

    thisApplication = cleanedName
    _applicationLogDir = logDir or (Path.home() / ".local" / "state" / cleanedName)
    _applicationLogDir.mkdir(parents=True, exist_ok=True)


def getApplication() -> str:
    """Return the active application context or fail fast if it was not set."""
    if not thisApplication:
        raise RuntimeError(
            "Application logging context has not been set. "
            "Call setApplication(name) in the entry point before importing modules "
            "that call getLogger()."
        )
    return thisApplication


def getApplicationLogDir() -> Path:
    """Return the active application log directory or fail fast if unset."""
    if _applicationLogDir is None:
        raise RuntimeError("Application log directory has not been initialised.")
    return _applicationLogDir


def _resolveLoggerName(name: Optional[str]) -> str:
    """Resolve an explicit logger name or the active application context."""
    if name:
        return name
    return getApplication()


def _defaultLogDir() -> Path:
    """
    Default base log directory for shared tools.

    Prefer a stable per-user location:
      ~/.local/state

    Log files are stored under ~/.local/state/{name}/{name}-{date}.log.
    """
    return Path.home() / ".local" / "state"


def _setupLogging(
    name: str,
    logDir: Optional[Path] = None,
    level: int = logging.INFO,
    includeConsole: bool = False,
) -> logging.Logger:
    """Set up logging with file and optional console handlers."""
    logger = _getLogger(name)
    logger.setLevel(level)

    if logDir is None:
        if name == getApplication():
            logDir = getApplicationLogDir()
        else:
            logDir = _defaultLogDir() / name

    logDir.mkdir(parents=True, exist_ok=True)
    date = datetime.date.today().isoformat()
    logFile = logDir / f"{name}-{date}.log"

    if str(logFile) not in _initialized_log_files:
        fileHandler = logging.FileHandler(logFile, encoding="utf-8")
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname).4s] %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fileHandler.setFormatter(formatter)
        logger.addHandler(fileHandler)
        _initialized_log_files.add(str(logFile))

    if includeConsole and not any(
        type(h) is logging.StreamHandler for h in logger.handlers
    ):
        consoleHandler = logging.StreamHandler()
        consoleFormatter = logging.Formatter(
            "[%(asctime)s] [%(levelname).4s] %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        consoleHandler.setFormatter(consoleFormatter)
        logger.addHandler(consoleHandler)

    return logger


def getLogger(
    name: Optional[str] = None,
    logDir: Optional[Path] = None,
    level: int = logging.INFO,
    includeConsole: bool = False,
    dryRun: bool = False,
) -> _OrganiseLoggerAdapter:
    """
    Convenience wrapper used by other scripts.

    If name is omitted, the active application context set by setApplication()
    is used. Passing name explicitly remains supported for specialised tools.

    Returns an _OrganiseLoggerAdapter with semantic log methods:
      doing(message, dryRunMessage=None) – logs '{prefix}message...'
      done(message, dryRunMessage=None)  – logs '...{prefix}message'
      info(message)            – logs '...message'
      multiline(lines)         – logs first line as info, remaining lines indented
      value(message, variable) – logs '...message: variable'
      action(message, dryRunMessage=None) – logs '...{prefix}message'
    Pass dryRun=True to insert '[] ' for doing, action, and done. The optional
    dryRunMessage replaces message only in dry-run mode. Existing calls remain
    valid; informational methods are deliberately not dry-run-prefixed.
    """
    loggerName = _resolveLoggerName(name)
    logger = _setupLogging(
        loggerName,
        logDir=logDir,
        level=level,
        includeConsole=includeConsole,
    )
    return _OrganiseLoggerAdapter(logger, dryRun=dryRun)


def setLogLevel(level: int, targetLogger: Optional[logging.Logger] = None) -> None:
    """Set logging level for the specified logger."""
    if targetLogger is None:
        targetLogger = _getLogger()

    targetLogger.setLevel(level)
    levelName = logging.getLevelName(level)
    if isinstance(targetLogger, _OrganiseLoggerAdapter):
        targetLogger.done(f"logging level changed to: {levelName}")
    else:
        targetLogger.info(f"...logging level changed to: {levelName}")


def cleanOldLogFiles(logDir: Path, daysToKeep: int) -> tuple[int, list[str]]:
    """
    Remove log files older than specified days.

    Returns (count_removed, list_of_removed_files).
    """
    targetDir = logDir.expanduser().resolve()
    if not targetDir.exists():
        return 0, []

    cutoffDate = datetime.datetime.now() - datetime.timedelta(days=daysToKeep)
    removedCount = 0
    removedFiles: list[str] = []

    for logFile in targetDir.glob("*.log"):
        try:
            fileTime = datetime.datetime.fromtimestamp(logFile.stat().st_mtime)
            if fileTime < cutoffDate:
                logFile.unlink()
                removedCount += 1
                removedFiles.append(logFile.name)
        except (OSError, ValueError):
            continue

    return removedCount, removedFiles


def drawBox(
    message: str,
    border_char: str = "─",
    corner_char: str = "+",
    side_char: str = "│",
    padding: int = 2,
    width: int | None = None,
    logger=None,
) -> None:
    """Print or log a formatted ASCII box around a message."""
    lines = message.splitlines()
    if not lines:
        lines = ["(empty message)"]

    if width is not None:
        if width <= 0:
            raise ValueError("width must be a positive integer when provided")

        wrappedLines: list[str] = []
        for line in lines:
            wrappedLines.extend(
                textwrap.wrap(
                    line,
                    width=width,
                    drop_whitespace=False,
                    replace_whitespace=False,
                )
                or [""]
            )
        lines = wrappedLines
        contentWidth = width
    else:
        contentWidth = max(len(line) for line in lines)

    innerWidth = contentWidth + padding * 2
    topBottom = corner_char + border_char * innerWidth + corner_char

    contentLines: list[str] = []
    for line in lines:
        padRight = innerWidth - len(line) - padding
        contentLines.append(
            f"{side_char}{' ' * padding}{line}{' ' * padRight}{side_char}"
        )

    outputLines = [
        topBottom,
        *contentLines,
        topBottom,
    ]

    if logger is not None:
        rawLogger = (
            logger.logger if isinstance(logger, logging.LoggerAdapter) else logger
        )
        for outLine in outputLines:
            rawLogger.info(outLine)
    else:
        for outLine in outputLines:
            print(outLine)
