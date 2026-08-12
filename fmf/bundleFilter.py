"""Filtering helpers for currently opened Unity bundle assets."""

from __future__ import annotations

from collections.abc import Iterable

from fmsat.fmf.structures import AssetInfo


def assetsFilter(
    assets: Iterable[AssetInfo],
    *,
    text: str = "",
    assetType: str = "",
) -> tuple[AssetInfo, ...]:
    """Filter assets by path ID, name, type, or container path."""

    query = text.strip().casefold()
    typeQuery = assetType.strip().casefold()
    matches: list[AssetInfo] = []
    for asset in assets:
        if typeQuery and typeQuery not in asset.assetType.casefold():
            continue
        haystack = " ".join(
            (
                str(asset.pathId),
                asset.assetName or "",
                asset.assetType,
                asset.containerPath or "",
            )
        ).casefold()
        if query and query not in haystack:
            continue
        matches.append(asset)
    return tuple(matches)
