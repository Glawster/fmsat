import sqlite3
from pathlib import Path

from fmsat.core.dataPaths import dataDirectoryGet, persistentDataPrepare


def _legacyDatabaseCreate(path: Path, imagePath: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE import_sessions " "(id INTEGER PRIMARY KEY, image_filename TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO import_sessions (image_filename) VALUES (?)",
            (str(imagePath),),
        )
        connection.commit()
    finally:
        connection.close()


def testDefaultDataDirectoryUsesXdgStateLocation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    assert dataDirectoryGet() == tmp_path / "fmsat"


def testLegacyDataIsCopiedAndScreenshotReferenceIsRewritten(tmp_path: Path) -> None:
    projectRoot = tmp_path / "project"
    legacyScreenshots = projectRoot / "data" / "screenshots"
    legacyScreenshots.mkdir(parents=True)
    legacyImage = legacyScreenshots / "formation.png"
    legacyImage.write_bytes(b"image")
    legacyDatabase = projectRoot / "data" / "fmsat.sqlite3"
    _legacyDatabaseCreate(legacyDatabase, legacyImage)
    persistentDirectory = tmp_path / "persistent"

    paths = persistentDataPrepare(projectRoot, persistentDirectory)

    assert paths.database.is_file()
    assert (paths.screenshots / "formation.png").read_bytes() == b"image"
    connection = sqlite3.connect(paths.database)
    try:
        storedPath = connection.execute("SELECT image_filename FROM import_sessions").fetchone()[0]
    finally:
        connection.close()
    assert storedPath == str(paths.screenshots / "formation.png")
    assert legacyDatabase.is_file()
    assert legacyImage.is_file()


def testExistingPersistentDatabaseIsNeverOverwritten(tmp_path: Path) -> None:
    projectRoot = tmp_path / "project"
    legacyDatabase = projectRoot / "data" / "fmsat.sqlite3"
    _legacyDatabaseCreate(legacyDatabase, projectRoot / "data" / "screenshots" / "old.png")
    persistentDirectory = tmp_path / "persistent"
    persistentDirectory.mkdir()
    persistentDatabase = persistentDirectory / "fmsat.sqlite3"
    persistentDatabase.write_bytes(b"existing")

    paths = persistentDataPrepare(projectRoot, persistentDirectory)

    assert paths.database.read_bytes() == b"existing"
