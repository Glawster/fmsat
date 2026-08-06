"""Filtering helpers for currently opened Unity bundle assets."""

from __future__ import annotations

from collections.abc import Iterable

from fmparser.structures import AssetInfo


def assetsFilter(
    assets: Iterable[AssetInfo],
    *,
    text: str = "",
    asset_type: str = "",
) -> tuple[AssetInfo, ...]:
    """Filter assets by path ID, name, type, or container path."""

    query = text.strip().casefold()
    type_query = asset_type.strip().casefold()
    matches: list[AssetInfo] = []
    for asset in assets:
        if type_query and type_query not in asset.asset_type.casefold():
            continue
        haystack = " ".join(
            (
                str(asset.path_id),
                asset.asset_name or "",
                asset.asset_type,
                asset.container_path or "",
            )
        ).casefold()
        if query and query not in haystack:
            continue
        matches.append(asset)
    return tuple(matches)
