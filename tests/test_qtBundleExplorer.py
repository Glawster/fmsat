from pathlib import Path

import pytest

from fmsat.fmf.structures import AssetInfo, AssetReference

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt  # noqa: E402

from fmsat.fmf.qtBundleExplorer import (  # noqa: E402
    AssetFilterProxyModel,
    AssetTableModel,
    ReferenceTableModel,
    _ReferencesSignals,
    _typeCounts,
)


def _assetCreate(pathId: int, name: str, assetType: str) -> AssetInfo:
    return AssetInfo(
        bundlePath=Path("sample.bundle"),
        pathId=pathId,
        assetName=name,
        assetType=assetType,
        containerPath=f"ui/{name}.asset",
        serializedSize=pathId,
    )


def testAssetTableModelExposesColumns(qapp) -> None:

    model = AssetTableModel((_assetCreate(2, "Beta", "Texture2D"),))

    assert model.rowCount() == 1
    assert model.columnCount() == 6
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Path ID"
    assert model.data(model.index(0, 1)) == "Beta"


def testAssetFilterProxyFiltersAssets(qapp) -> None:

    # _applicationCreate()
    model = AssetTableModel(
        (
            _assetCreate(1, "PlayerPanel", "VisualTreeAsset"),
            _assetCreate(2, "PlayerIcon", "Texture2D"),
        )
    )
    proxy = AssetFilterProxyModel()
    proxy.setSourceModel(model)

    proxy.filtersSet(text="player", assetType="VisualTree")

    assert proxy.rowCount() == 1
    assert proxy.data(proxy.index(0, 1)) == "PlayerPanel"


def testAssetFilterProxyFiltersSerializedSearchText(qapp) -> None:

    # _applicationCreate()
    model = AssetTableModel(
        (
            _assetCreate(1, "Panel", "VisualTreeAsset"),
            _assetCreate(2, "PlayerIcon", "Texture2D"),
        )
    )
    proxy = AssetFilterProxyModel()
    proxy.setSourceModel(model)
    proxy.serializedSearchTextSet({1: '{"m_name": "latest scores"}'})

    proxy.filtersSet(text="Latest Scores", assetType="")

    assert proxy.rowCount() == 1
    assert proxy.data(proxy.index(0, 1)) == "Panel"


def testTypeCountsSortsByCountThenType(qapp) -> None:

    assets = (
        _assetCreate(1, "PlayerPanel", "VisualTreeAsset"),
        _assetCreate(2, "PlayerIcon", "Texture2D"),
        _assetCreate(3, "Scores", "VisualTreeAsset"),
    )

    assert _typeCounts(assets) == (("VisualTreeAsset", 2), ("Texture2D", 1))


def testReferenceTableModelExposesReferences() -> None:

    # _applicationCreate()
    model = ReferenceTableModel(
        (
            AssetReference(
                pathId=42,
                assetType="VisualTreeAsset",
                assetName="LatestScores",
                relationship="m_VisualTree",
            ),
        )
    )

    assert model.rowCount() == 1
    assert model.columnCount() == 4
    assert model.headerData(2, Qt.Orientation.Horizontal) == "Name"
    assert model.data(model.index(0, 0)) == 42
    assert model.data(model.index(0, 2)) == "LatestScores"


def testReferencesSignalAcceptsLargeUnityPathIds(qapp) -> None:

    # _applicationCreate()
    signals = _ReferencesSignals()
    emitted: list[tuple[int, int, object]] = []
    large_pathId = 8889112869717200915

    signals.finished.connect(
        lambda generation, asset_id, refs: emitted.append((generation, asset_id, refs))
    )
    signals.finished.emit(1, large_pathId, ())

    assert emitted == [(1, large_pathId, ())]
