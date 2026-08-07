"""Persistent FMSAT data locations and legacy repository migration."""

from __future__ import annotations

import os
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


class PersistentDataError(RuntimeError):
    """Raised when persistent application data cannot be prepared safely."""


@dataclass(frozen=True, slots=True)
class PersistentDataPaths:
    """Owned locations for the database, screenshots, and future user data."""

    directory: Path
    database: Path
    screenshots: Path


def dataDirectoryGet() -> Path:
    """Return the XDG-compatible FMSAT persistent-state directory."""

    configured = os.environ.get("XDG_STATE_HOME")
    root = Path(configured).expanduser() if configured else Path.home() / ".local" / "state"
    return root / "fmsat"


def persistentDataPrepare(
    projectRoot: Path,
    dataDirectory: Path | None = None,
) -> PersistentDataPaths:
    """Prepare persistent paths and copy legacy repository data once."""

    directory = (dataDirectory or dataDirectoryGet()).expanduser().resolve()
    paths = PersistentDataPaths(
        directory=directory,
        database=directory / "fmsat.sqlite3",
        screenshots=directory / "screenshots",
    )
    legacyDirectory = (projectRoot / "data").resolve()
    legacyDatabase = legacyDirectory / "fmsat.sqlite3"
    legacyScreenshots = legacyDirectory / "screenshots"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        paths.screenshots.mkdir(parents=True, exist_ok=True)
        if not paths.database.exists() and legacyDatabase.is_file():
            _databaseCopy(legacyDatabase, paths.database)
            _screenshotsCopy(legacyScreenshots, paths.screenshots)
            _screenshotReferencesRewrite(
                paths.database,
                legacyScreenshots,
                paths.screenshots,
            )
    except (OSError, sqlite3.Error) as exc:
        raise PersistentDataError(f"Unable to prepare persistent FMSAT data: {exc}") from exc
    return paths


def _databaseCopy(source: Path, destination: Path) -> None:
    temporary = destination.parent / f".{destination.name}-{uuid4().hex}.tmp"
    try:
        shutil.copy2(source, temporary)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _screenshotsCopy(source: Path, destination: Path) -> None:
    if not source.is_dir():
        return
    for sourcePath in source.iterdir():
        if not sourcePath.is_file():
            continue
        destinationPath = destination / sourcePath.name
        if not destinationPath.exists():
            shutil.copy2(sourcePath, destinationPath)


def _screenshotReferencesRewrite(
    database: Path,
    legacyScreenshots: Path,
    persistentScreenshots: Path,
) -> None:
    connection = sqlite3.connect(database)
    try:
        tableExists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'import_sessions'"
        ).fetchone()
        if tableExists is None:
            return
        rows = connection.execute("SELECT id, image_filename FROM import_sessions").fetchall()
        legacyRoot = legacyScreenshots.resolve()
        updates: list[tuple[str, int]] = []
        for identifier, value in rows:
            sourcePath = Path(value)
            try:
                relative = sourcePath.resolve().relative_to(legacyRoot)
            except ValueError:
                continue
            updates.append((str(persistentScreenshots / relative), int(identifier)))
        connection.executemany(
            "UPDATE import_sessions SET image_filename = ? WHERE id = ?",
            updates,
        )
        connection.commit()
    finally:
        connection.close()
