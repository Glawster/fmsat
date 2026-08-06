"""Read-only Unity asset bundle inspection for Football Manager skins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
import json
from pathlib import Path
from typing import Any

from fmparser.structures import AssetData, AssetInfo, AssetReference, BundleInfo


class BundleError(RuntimeError):
    """Base exception for user-facing bundle inspection failures."""


class BundleDependencyError(BundleError):
    """Raised when an optional bundle dependency is not installed."""


class BundleFormatError(BundleError):
    """Raised when a file cannot be read as a Unity bundle."""


class BundleAssetError(BundleError):
    """Raised when a specific asset cannot be inspected."""


class BundleReader(ABC):
    """Application-owned read-only interface for Unity bundle inspection."""

    @abstractmethod
    def open(self, path: Path) -> BundleInfo:
        """Open one bundle file and return bundle metadata."""

    @abstractmethod
    def assetsList(self) -> Sequence[AssetInfo]:
        """Return assets from the currently opened bundle."""

    @abstractmethod
    def assetRead(self, asset_id: int) -> AssetData:
        """Return safely readable data for one asset."""

    @abstractmethod
    def assetExport(self, asset_id: int, destination: Path) -> Path:
        """Export one decoded asset when safe and supported."""


class UnityPyBundleReader(BundleReader):
    """UnityPy-backed implementation of :class:`BundleReader`."""

    def __init__(self) -> None:
        _configureTypeTreeHelper()

        self._environment: Any | None = None
        self._path: Path | None = None
        self._bundle_info: BundleInfo | None = None
        self._assets: tuple[AssetInfo, ...] = ()
        self._objects_by_id: dict[int, Any] = {}
        self._assets_by_id: dict[int, AssetInfo] = {}
        self._serialized_search_text: dict[int, str] = {}
        self._references_by_id: dict[int, tuple[AssetReference, ...]] = {}
        self._reverse_references_by_id: dict[int, tuple[AssetReference, ...]] = {}
        self._reference_index_built = False

    def open(self, path: Path) -> BundleInfo:
        bundle_path = path.expanduser().resolve()
        if not bundle_path.is_file():
            raise FileNotFoundError(f"Bundle file does not exist: {bundle_path}")

        try:
            import UnityPy  # type: ignore[import-not-found]
        except ImportError as error:
            raise BundleDependencyError(
                "UnityPy is required for bundle inspection. Install with "
                "`pip install .[bundles]`."
            ) from error

        try:
            environment = UnityPy.load(str(bundle_path))
        except Exception as error:  # noqa: BLE001 - adapter converts library errors.
            raise BundleFormatError(f"Could not open Unity bundle: {error}") from error

        self._environment = environment
        self._path = bundle_path
        self._serialized_search_text = {}
        self._references_by_id = {}
        self._reverse_references_by_id = {}
        self._reference_index_built = False
        self._objects_by_id = {
            int(getattr(item, "path_id", 0)): item
            for item in getattr(environment, "objects", [])
            if getattr(item, "path_id", None) is not None
        }
        container_paths = self._containerPaths(environment)
        self._assets = tuple(
            self._assetInfo(bundle_path, item, container_paths.get(int(getattr(item, "path_id", 0))))
            for item in getattr(environment, "objects", [])
        )
        self._assets_by_id = {asset.path_id: asset for asset in self._assets}

        info = BundleInfo(
            path=bundle_path,
            file_name=bundle_path.name,
            size=bundle_path.stat().st_size,
            signature=_bundleSignature(bundle_path),
            unity_version=self._unityVersion(environment),
            asset_count=len(self._assets),
            external_references=self._externalReferences(environment),
        )
        self._bundle_info = info
        return info

    def assetsList(self) -> Sequence[AssetInfo]:
        self._requireOpen()
        return self._assets

    def assetRead(self, asset_id: int) -> AssetData:
        self._requireOpen()
        asset = self._assetById(asset_id)
        unity_object = self._objects_by_id.get(asset_id)
        if unity_object is None:
            raise BundleAssetError(f"Asset not found: {asset_id}")

        try:
            data = unity_object.read()
        except Exception as error:  # noqa: BLE001 - adapter converts library errors.
            return AssetData(
                asset=asset,
                representation="unsupported",
                message=f"{asset.asset_type} could not be decoded safely: {error}",
            )

        if asset.asset_type == "TextAsset":
            text = _textAssetContent(data)
            if text is not None:
                return AssetData(asset=asset, representation="original-or-serialized-text", text=text)

        if asset.asset_type in {"VisualTreeAsset", "MonoBehaviour"} or "StyleSheet" in asset.asset_type:
            structure = self._typeTree(unity_object)
            if structure:
                return AssetData(
                    asset=asset,
                    representation="serialized-unity-object",
                    text=json.dumps(structure, indent=2, sort_keys=True, default=str),
                    structure=structure,
                    message="Serialized Unity object data; this is not guaranteed to be original source.",
                )

        if asset.asset_type in {"Texture2D", "Sprite"}:
            return AssetData(
                asset=asset,
                representation="unsupported",
                message=f"{asset.asset_type} preview/export is not implemented in this milestone.",
            )

        structure = self._typeTree(unity_object)
        if structure:
            return AssetData(
                asset=asset,
                representation="serialized-unity-object",
                text=json.dumps(structure, indent=2, sort_keys=True, default=str),
                structure=structure,
                message="Serialized Unity object data; this is not original source.",
            )

        return AssetData(
            asset=asset,
            representation="unsupported",
            message=f"{asset.asset_type} is not decoded by the first milestone.",
        )

    def assetExport(self, asset_id: int, destination: Path) -> Path:
        data = self.assetRead(asset_id)
        if data.text is None:
            raise BundleAssetError(
                f"Asset {asset_id} has no safe textual export in this milestone: {data.message}"
            )

        target_dir = destination.expanduser().resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        name = data.asset.asset_name or str(data.asset.path_id)
        safe_name = "".join(char if char.isalnum() or char in "._-" else "_" for char in name)
        target = target_dir / f"{safe_name}.{_extensionFor(data.representation)}"
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite existing file: {target}")
        target.write_text(data.text, encoding="utf-8")
        return target

    def assetSearchText(self, asset_id: int) -> str:
        """Return cached searchable serialized text for one asset."""

        self._requireOpen()
        if asset_id in self._serialized_search_text:
            return self._serialized_search_text[asset_id]

        asset = self._assetById(asset_id)
        unity_object = self._objects_by_id.get(asset_id)
        if unity_object is None:
            raise BundleAssetError(f"Asset not found: {asset_id}")

        parts = [
            str(asset.path_id),
            asset.asset_name or "",
            asset.asset_type,
            asset.container_path or "",
        ]
        structure = self._typeTree(unity_object)
        if structure:
            parts.append(json.dumps(structure, sort_keys=True, default=str))
        if asset.asset_type == "TextAsset":
            try:
                text = _textAssetContent(unity_object.read())
            except Exception:  # noqa: BLE001 - deep search remains best effort.
                text = None
            if text:
                parts.append(text)

        search_text = "\n".join(part for part in parts if part).casefold()
        self._serialized_search_text[asset_id] = search_text
        return search_text

    def assetReferences(self, asset_id: int) -> tuple[AssetReference, ...]:
        """Return cached references from one asset to other known assets."""

        self._requireOpen()
        if asset_id in self._references_by_id:
            return self._references_by_id[asset_id]

        self._assetById(asset_id)
        unity_object = self._objects_by_id.get(asset_id)
        if unity_object is None:
            raise BundleAssetError(f"Asset not found: {asset_id}")

        refs = _referencesFromStructure(self._typeTree(unity_object))
        enriched = tuple(_referenceEnrich(ref, self._assets_by_id) for ref in refs)
        self._references_by_id[asset_id] = enriched
        return enriched

    def referencesBuild(self) -> None:
        """Build the forward and reverse reference indexes once for this bundle."""

        self._requireOpen()
        if self._reference_index_built:
            return

        reverse: dict[int, dict[tuple[int | None, str | None], AssetReference]] = {}
        for asset in self._assets:
            for reference in self.assetReferences(asset.path_id):
                if reference.path_id is None:
                    continue
                source = AssetReference(
                    path_id=asset.path_id,
                    asset_path=asset.container_path,
                    asset_type=asset.asset_type,
                    asset_name=asset.asset_name,
                    relationship=reference.relationship,
                )
                key = (source.path_id, source.relationship)
                reverse.setdefault(reference.path_id, {}).setdefault(key, source)
        self._reverse_references_by_id = {
            path_id: tuple(refs.values()) for path_id, refs in reverse.items()
        }
        self._reference_index_built = True

    def reverseReferences(self, asset_id: int) -> tuple[AssetReference, ...]:
        """Return assets that reference the selected asset."""

        self._requireOpen()
        if not self._reference_index_built:
            return ()
        return self._reverse_references_by_id.get(asset_id, ())

    def assetGraph(self, asset_id: int) -> dict[str, Any]:
        """Return a read-only graph around the selected asset."""

        self.referencesBuild()
        asset = self._assetById(asset_id)
        return {
            "asset": _assetGraphNode(asset),
            "references": tuple(_referenceGraphNode(ref) for ref in self.assetReferences(asset_id)),
            "referenced_by": tuple(
                _referenceGraphNode(ref) for ref in self.reverseReferences(asset_id)
            ),
        }

    def assetGraphText(self, asset_id: int, format_name: str) -> str:
        """Serialize the selected asset graph as JSON or Graphviz DOT."""

        graph = self.assetGraph(asset_id)
        normalized = format_name.casefold()
        if normalized == "json":
            return json.dumps(graph, indent=2, sort_keys=True, default=str) + "\n"
        if normalized == "dot":
            return _graphDot(graph)
        raise BundleAssetError(f"Unsupported graph export format: {format_name}")

    def _requireOpen(self) -> None:
        if self._environment is None or self._path is None:
            raise BundleError("No bundle is open.")

    def _assetById(self, asset_id: int) -> AssetInfo:
        for asset in self._assets:
            if asset.path_id == asset_id:
                return asset
        raise BundleAssetError(f"Asset not found: {asset_id}")

    def _assetInfo(self, bundle_path: Path, unity_object: Any, container_path: str | None) -> AssetInfo:
        path_id = int(getattr(unity_object, "path_id", 0))
        asset_type = _objectTypeName(unity_object)
        asset_name = self._assetName(unity_object)
        return AssetInfo(
            bundle_path=bundle_path,
            path_id=path_id,
            asset_type=asset_type,
            asset_name=asset_name,
            serialized_size=_serializedSize(unity_object),
            container_path=container_path,
            dependencies=self._dependencies(unity_object),
            external_references=self._externalReferences(self._environment),
        )

    def _assetName(self, obj) -> str:
        try:
            name = obj.peek_name()
            if name:
                return str(name)
        except Exception:
            pass

        return ""

    def _typeTree(self, unity_object: Any) -> dict[str, Any]:
        try:
            value = unity_object.read_typetree()
        except Exception:  # noqa: BLE001 - unsupported typetrees are expected.
            return {}
        return value if isinstance(value, dict) else {"value": value}

    def _dependencies(self, unity_object: Any) -> tuple[AssetReference, ...]:
        refs: list[AssetReference] = []
        for candidate in ("dependencies", "assets_file"):
            value = getattr(unity_object, candidate, None)
            if value is None:
                continue
            refs.append(AssetReference(external=str(value)))
        return tuple(refs)

    def _containerPaths(self, environment: Any) -> dict[int, str]:
        paths: dict[int, str] = {}
        container = getattr(environment, "container", {}) or {}
        for container_path, unity_object in container.items():
            path_id = getattr(unity_object, "path_id", None)
            if path_id is not None:
                paths[int(path_id)] = str(container_path)
        return paths

    def _externalReferences(self, environment: Any | None) -> tuple[str, ...]:
        if environment is None:
            return ()
        values: list[str] = []
        for attr in ("files", "cabinet", "assets"):
            value = getattr(environment, attr, None)
            if value:
                values.append(str(value))
        return tuple(dict.fromkeys(values))

    def _unityVersion(self, environment: Any) -> str | None:
        for attr in ("unity_version", "version"):
            value = getattr(environment, attr, None)
            if value:
                return str(value)
        return None


def _bundleSignature(path: Path) -> str:
    data = path.read_bytes()[:32]
    if data.startswith((b"UnityFS", b"UnityWeb", b"UnityRaw")):
        return data.split(b"\x00", 1)[0].decode("ascii", errors="replace")
    return data[:8].hex(" ")


def _configureTypeTreeHelper() -> None:
    try:
        from UnityPy.helpers import TypeTreeHelper
    except Exception:  # noqa: BLE001 - UnityPy may be absent until open() reports dependency errors.
        return
    TypeTreeHelper.read_typetree_boost = False


def _referencesFromStructure(structure: Any) -> tuple[AssetReference, ...]:
    refs: list[AssetReference] = []
    _referencesCollect(structure, "", refs)
    deduped: dict[tuple[int | None, str | None], AssetReference] = {}
    for ref in refs:
        key = (ref.path_id, ref.relationship)
        deduped.setdefault(key, ref)
    return tuple(deduped.values())


def _referencesCollect(value: Any, relationship: str, refs: list[AssetReference]) -> None:
    if isinstance(value, dict):
        path_id = _pathIdFromMapping(value)
        if path_id not in (None, 0):
            refs.append(AssetReference(path_id=path_id, relationship=relationship or None))
            return
        for key, child in value.items():
            child_relationship = f"{relationship}.{key}" if relationship else str(key)
            _referencesCollect(child, child_relationship, refs)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            child_relationship = f"{relationship}[{index}]" if relationship else f"[{index}]"
            _referencesCollect(child, child_relationship, refs)


def _pathIdFromMapping(value: dict[Any, Any]) -> int | None:
    for key in ("m_PathID", "path_id", "PathID", "pathID"):
        candidate = value.get(key)
        if isinstance(candidate, int):
            return candidate
        if isinstance(candidate, str):
            try:
                return int(candidate)
            except ValueError:
                return None
    return None


def _referenceEnrich(
    reference: AssetReference,
    assets_by_id: dict[int, AssetInfo],
) -> AssetReference:
    if reference.path_id is None:
        return reference
    asset = assets_by_id.get(reference.path_id)
    if asset is None:
        return reference
    return AssetReference(
        path_id=reference.path_id,
        asset_path=asset.container_path,
        asset_type=asset.asset_type,
        asset_name=asset.asset_name,
        relationship=reference.relationship,
        external=reference.external,
    )


def _assetGraphNode(asset: AssetInfo) -> dict[str, Any]:
    return {
        "path_id": asset.path_id,
        "type": asset.asset_type,
        "name": asset.asset_name,
        "container": asset.container_path,
        "serialized_size": asset.serialized_size,
    }


def _referenceGraphNode(reference: AssetReference) -> dict[str, Any]:
    return {
        "path_id": reference.path_id,
        "type": reference.asset_type,
        "name": reference.asset_name,
        "container": reference.asset_path,
        "relationship": reference.relationship,
        "external": reference.external,
    }


def _graphDot(graph: dict[str, Any]) -> str:
    asset = graph["asset"]
    selected_id = str(asset["path_id"])
    lines = ["digraph asset_graph {", "  rankdir=LR;"]
    lines.append(f'  "{_dotEscape(selected_id)}" [label="{_dotEscape(_graphLabel(asset))}"];')
    for reference in graph["references"]:
        target_id = str(reference["path_id"])
        lines.append(
            f'  "{_dotEscape(target_id)}" [label="{_dotEscape(_graphLabel(reference))}"];'
        )
        lines.append(
            f'  "{_dotEscape(selected_id)}" -> "{_dotEscape(target_id)}"'
            f' [label="{_dotEscape(reference.get("relationship") or "")}"];'
        )
    for reference in graph["referenced_by"]:
        source_id = str(reference["path_id"])
        lines.append(
            f'  "{_dotEscape(source_id)}" [label="{_dotEscape(_graphLabel(reference))}"];'
        )
        lines.append(
            f'  "{_dotEscape(source_id)}" -> "{_dotEscape(selected_id)}"'
            f' [label="{_dotEscape(reference.get("relationship") or "")}"];'
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def _graphLabel(node: dict[str, Any]) -> str:
    name = node.get("name") or "(unnamed)"
    return f"{name}\\n{node.get('type') or 'unknown'}\\n{node.get('path_id')}"


def _dotEscape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _objectTypeName(unity_object: Any) -> str:
    value = getattr(unity_object, "type", None)
    name = getattr(value, "name", None)
    if name:
        return str(name)
    return str(value or "unknown")


def _serializedSize(unity_object: Any) -> int | None:
    for attr in ("byte_size", "size", "serialized_size"):
        value = getattr(unity_object, attr, None)
        if isinstance(value, int):
            return value
    return None


def _textAssetContent(data: Any) -> str | None:
    for attr in ("script", "m_Script"):
        value = getattr(data, attr, None)
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, str):
            return value
    return None


def _extensionFor(representation: str) -> str:
    if "text" in representation:
        return "txt"
    return "json"
