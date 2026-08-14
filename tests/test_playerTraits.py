"""Canonical Football Manager player-trait vocabulary tests."""

from fmsat.football.trait import PlayerTraitIdentity, playerTraits


def testPlayerTraitCatalogueCapturesFm26Selector() -> None:
    """Every distinct trait supplied from the FM26 selector is represented."""

    assert len(PlayerTraitIdentity) == 61
    assert len(playerTraits) == 61
    assert len({trait.name for trait in playerTraits}) == 61
    assert all(trait.identity is not None for trait in playerTraits)


def testPlayerTraitCataloguePreservesDisplayedLabels() -> None:
    """Stable identities retain the exact labels displayed by the game."""

    assert PlayerTraitIdentity.runsWithBallThroughTheCentre.value == (
        "Runs With Ball Through The Centre"
    )
    assert PlayerTraitIdentity.staysBackAtAllTimes.value == "Stays Back At All Times"
    assert PlayerTraitIdentity.playsOneTwos.value == "Plays One-Twos"
    assert PlayerTraitIdentity.playsBallWithFeet.value == "Plays Ball With Feet"
