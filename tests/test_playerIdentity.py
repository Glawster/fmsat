"""Player-name cleanup and evidence reconciliation tests."""

from fmsat.core.parser import ExtractedPlayer
from fmsat.core.playerIdentity import (
    playerEvidenceMatches,
    playerNameClean,
    playerNameIsUncertain,
    preferredPlayerName,
)


def _player(name: str, *, passing: int = 14) -> ExtractedPlayer:
    return ExtractedPlayer(
        name,
        "M (C)",
        "105",
        "125",
        {"passing": passing, "vision": 13},
        0.92,
    )


def testCleanupPreservesLegitimateNameStructure() -> None:
    assert playerNameClean("  O'Neil,   J.-P.  ") == "O'Neil, J.-P."
    assert not playerNameIsUncertain("O'Neil, J.-P.")


def testShortOcrFragmentIsFlaggedButNotSilentlyRemoved() -> None:
    assert playerNameClean("Smith,,  Qe Ella") == "Smith, Qe Ella"
    assert playerNameIsUncertain("Smith, Qe Ella")


def testCleanerCrossCaptureRenderingWinsWithCorroboratingFacts() -> None:
    noisy = _player("Smith, Qe Ella")
    clean = _player("Smith, Ella")

    assert playerEvidenceMatches(noisy, clean)
    assert preferredPlayerName(noisy, clean) == "Smith, Ella"


def testSimilarNameWithoutEnoughFactualEvidenceDoesNotMerge() -> None:
    first = _player("Mason, Re Ellie", passing=14)
    second = ExtractedPlayer("Mason, Ellie", "ST (C)", "", "", {"passing": 9}, 0.9)

    assert not playerEvidenceMatches(first, second)
