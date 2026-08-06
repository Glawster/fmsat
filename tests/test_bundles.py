import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from fmparser.bundles import BundleFormatError, UnityPyBundleReader


class _Type:
    def __init__(self, name: str) -> None:
        self.name = name


class _Object:
    byte_size = 42

    def __init__(
        self,
        path_id: int = 123,
        name: str = "hello",
        asset_type: str = "TextAsset",
        structure: dict[str, object] | None = None,
    ) -> None:
        self.path_id = path_id
        self.type = _Type(asset_type)
        self._name = name
        self._structure = structure or {"m_Name": name}

    def peek_name(self) -> str:
        return self._name

    def read(self) -> SimpleNamespace:
        return SimpleNamespace(name="hello", script=b"hello world")

    def read_typetree(self) -> dict[str, object]:
        return self._structure


def testBundleReaderValidatesMissingPath(tmp_path: Path) -> None:
    reader = UnityPyBundleReader()

    with pytest.raises(FileNotFoundError):
        reader.open(tmp_path / "missing.bundle")


def testBundleReaderConvertsAdapterErrors(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    sample = tmp_path / "sample.bundle"
    sample.write_bytes(b"UnityFS\x00")

    def load(path: str) -> object:
        del path
        raise ValueError("bad bundle")

    monkeypatch.setitem(sys.modules, "UnityPy", SimpleNamespace(load=load))

    with pytest.raises(BundleFormatError, match="Could not open Unity bundle"):
        UnityPyBundleReader().open(sample)


def testBundleReaderListsAndReadsAssets(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    sample = tmp_path / "sample.bundle"
    sample.write_bytes(b"UnityFS\x00")
    unity_object = _Object(structure={"m_Name": "hello", "target": {"m_PathID": 456}})
    target_object = _Object(path_id=456, name="target", asset_type="VisualTreeAsset")
    environment = SimpleNamespace(
        objects=[unity_object, target_object],
        container={"assets/ui/hello.txt": unity_object},
        unity_version="6000.0",
        files=[],
    )
    monkeypatch.setitem(sys.modules, "UnityPy", SimpleNamespace(load=lambda path: environment))

    reader = UnityPyBundleReader()
    info = reader.open(sample)
    assets = reader.assetsList()
    data = reader.assetRead(123)
    search_text = reader.assetSearchText(123)
    references = reader.assetReferences(123)
    reader.referencesBuild()
    reverse_references = reader.reverseReferences(456)
    graph_json = json.loads(reader.assetGraphText(123, "json"))
    graph_dot = reader.assetGraphText(123, "dot")

    assert info.signature == "UnityFS"
    assert info.asset_count == 2
    assert info.unity_version == "6000.0"
    assert assets[0].path_id == 123
    assert assets[0].asset_name == "hello"
    assert assets[0].container_path == "assets/ui/hello.txt"
    assert data.text == "hello world"
    assert data.representation == "original-or-serialized-text"
    assert "hello world" in search_text
    assert "m_name" in search_text
    assert references[0].path_id == 456
    assert references[0].asset_name == "target"
    assert references[0].asset_type == "VisualTreeAsset"
    assert references[0].relationship == "target"
    assert reverse_references[0].path_id == 123
    assert reverse_references[0].asset_name == "hello"
    assert reverse_references[0].relationship == "target"
    assert graph_json["asset"]["path_id"] == 123
    assert graph_json["references"][0]["path_id"] == 456
    assert '"123" -> "456"' in graph_dot
