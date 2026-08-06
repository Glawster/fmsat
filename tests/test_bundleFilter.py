from pathlib import Path

from fmparser.bundleFilter import assetsFilter
from fmparser.structures import AssetInfo


def _assetCreate(path_id: int, name: str, asset_type: str, container: str) -> AssetInfo:
    return AssetInfo(
        bundle_path=Path("sample.bundle"),
        path_id=path_id,
        asset_name=name,
        asset_type=asset_type,
        container_path=container,
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

    assert assetsFilter(assets, text="player", asset_type="VisualTree") == (assets[0],)
