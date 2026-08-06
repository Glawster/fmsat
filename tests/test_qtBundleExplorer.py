from pathlib import Path

import pytest

from fmparser.structures import AssetInfo, AssetReference

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, Qt  # noqa: E402

from fmparser.qtBundleExplorer import (  # noqa: E402
    AssetFilterProxyModel,
    AssetTableModel,
    ReferenceTableModel,
    _ReferencesSignals,
    _typeCounts,
)


def _applicationCreate() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def _assetCreate(path_id: int, name: str, asset_type: str) -> AssetInfo:
    return AssetInfo(
        bundle_path=Path("sample.bundle"),
        path_id=path_id,
        asset_name=name,
        asset_type=asset_type,
        container_path=f"ui/{name}.asset",
        serialized_size=path_id,
    )


def testAssetTableModelExposesColumns() -> None:
    _applicationCreate()
    model = AssetTableModel((_assetCreate(2, "Beta", "Texture2D"),))

    assert model.rowCount() == 1
    assert model.columnCount() == 6
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Path ID"
    assert model.data(model.index(0, 1)) == "Beta"


def testAssetFilterProxyFiltersAssets() -> None:
    _applicationCreate()
    model = AssetTableModel(
        (
            _assetCreate(1, "PlayerPanel", "VisualTreeAsset"),
            _assetCreate(2, "PlayerIcon", "Texture2D"),
        )
    )
    proxy = AssetFilterProxyModel()
    proxy.setSourceModel(model)

    proxy.filtersSet(text="player", asset_type="VisualTree")

    assert proxy.rowCount() == 1
    assert proxy.data(proxy.index(0, 1)) == "PlayerPanel"


def testAssetFilterProxyFiltersSerializedSearchText() -> None:
    _applicationCreate()
    model = AssetTableModel(
        (
            _assetCreate(1, "Panel", "VisualTreeAsset"),
            _assetCreate(2, "PlayerIcon", "Texture2D"),
        )
    )
    proxy = AssetFilterProxyModel()
    proxy.setSourceModel(model)
    proxy.serializedSearchTextSet({1: '{"m_name": "latest scores"}'})

    proxy.filtersSet(text="Latest Scores", asset_type="")

    assert proxy.rowCount() == 1
    assert proxy.data(proxy.index(0, 1)) == "Panel"


def testTypeCountsSortsByCountThenType() -> None:
    assets = (
        _assetCreate(1, "PlayerPanel", "VisualTreeAsset"),
        _assetCreate(2, "PlayerIcon", "Texture2D"),
        _assetCreate(3, "Scores", "VisualTreeAsset"),
    )

    assert _typeCounts(assets) == (("VisualTreeAsset", 2), ("Texture2D", 1))


def testReferenceTableModelExposesReferences() -> None:
    _applicationCreate()
    model = ReferenceTableModel(
        (
            AssetReference(
                path_id=42,
                asset_type="VisualTreeAsset",
                asset_name="LatestScores",
                relationship="m_VisualTree",
            ),
        )
    )

    assert model.rowCount() == 1
    assert model.columnCount() == 4
    assert model.headerData(2, Qt.Orientation.Horizontal) == "Name"
    assert model.data(model.index(0, 0)) == 42
    assert model.data(model.index(0, 2)) == "LatestScores"


def testReferencesSignalAcceptsLargeUnityPathIds() -> None:
    _applicationCreate()
    signals = _ReferencesSignals()
    emitted: list[tuple[int, int, object]] = []
    large_path_id = 8889112869717200915

    signals.finished.connect(lambda generation, asset_id, refs: emitted.append((generation, asset_id, refs)))
    signals.finished.emit(1, large_path_id, ())

    assert emitted == [(1, large_path_id, ())]
