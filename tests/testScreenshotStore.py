"""Managed screenshot storage tests."""

from datetime import datetime

import numpy as np

from fmsat.core.screenshotStore import ScreenshotStore


def testCaptureUsesReadableUniqueSafeNameAndCanBeRemoved(tmp_path) -> None:
    store = ScreenshotStore(tmp_path / "screenshots")
    image = np.zeros((20, 30, 3), dtype=np.uint8)

    path = store.captureSave(
        image,
        "Squad",
        "First Team / U21s",
        "SQUAD_ATTRIBUTES",
        capturedAt=datetime(2026, 8, 5, 11, 45),
        identifier="A1B2C3D4",
    )

    assert path.name == (
        "20260805-114500_squad-first-team-u21s_squad-attributes_a1b2c3d4.png"
    )
    assert path.is_file()
    assert store.capturesRemove([path]) == []
    assert not path.exists()


def testRemovalRejectsAPathOutsideManagedStorage(tmp_path) -> None:
    store = ScreenshotStore(tmp_path / "screenshots")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"not managed")

    assert store.capturesRemove([outside]) == [outside.resolve()]
    assert outside.exists()


def testRemovalIgnoresMissingLegacyImageReference(tmp_path) -> None:
    store = ScreenshotStore(tmp_path / "screenshots")
    legacyReference = tmp_path / "clipboard"

    assert store.capturesRemove([legacyReference]) == []
