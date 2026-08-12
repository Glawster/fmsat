from pathlib import Path

from fmsat.fmf.bundleFilter import assetsFilter
from fmsat.fmf.structures import AssetInfo


def _assetCreate(pathId: int, name: str, assetType: str, container: str) -> AssetInfo:
    return AssetInfo(
        bundlePath=Path("sample.bundle"),
        pathId=pathId,
        assetName=name,
        assetType=assetType,
        containerPath=container,
    )


def testAssetsFilterMatchesNameTypeContainerAndPathId() -> None:

    assets = (
        _assetCreate(10, "PlayerPanel", "VisualTreeAsset", "ui/player.uxml"),
        _assetCreate(20, "ClubLogo", "Texture2D", "ui/images/club.png"),
    )

    assert assetsFilter(assets, text="player") == (assets[0],)
    assert assetsFilter(assets, text="texture") == (assets[1],)
    assert assetsFilter(assets, text="club.png") == (assets[1],)
    assert assetsFilter(assets, text="20") == (assets[1],)


def testAssetsFilterAppliesTypeFilter() -> None:

    assets = (
        _assetCreate(10, "PlayerPanel", "VisualTreeAsset", "ui/player.uxml"),
        _assetCreate(20, "PlayerIcon", "Texture2D", "ui/player.png"),
    )

    assert assetsFilter(assets, text="player", assetType="VisualTree") == (assets[0],)
