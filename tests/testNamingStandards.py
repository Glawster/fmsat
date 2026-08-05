"""Enforce the repository's camelCase source naming standard."""

from __future__ import annotations

import ast
from pathlib import Path

allowedIdentifiers = {
    "_",
    "SQUAD_ATTRIBUTES",
    "TACTIC_FORMATION",
    "TACTIC_IN_POSSESSION",
    "TACTIC_OUT_OF_POSSESSION",
    "tmp_path",
}
allowedFileNames = {"__init__.py", "conftest.py"}


def _hasInternalUnderscore(identifier: str) -> bool:
    if identifier.startswith("__") and identifier.endswith("__"):
        return False
    return "_" in identifier.lstrip("_")


def testPythonFileNamesUseCamelCase() -> None:
    projectPath = Path(__file__).parents[1]
    invalidNames = sorted(
        path.name
        for path in projectPath.rglob("*.py")
        if "__pycache__" not in path.parts
        and path.name not in allowedFileNames
        and "_" in path.stem
    )

    assert invalidNames == []


def testProjectOwnedIdentifiersUseCamelCase() -> None:
    projectPath = Path(__file__).parents[1]
    invalidIdentifiers: list[str] = []
    for path in projectPath.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifier = node.id
                if identifier not in allowedIdentifiers and _hasInternalUnderscore(identifier):
                    invalidIdentifiers.append(f"{path.name}:{node.lineno}:{identifier}")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                arguments = [
                    *node.args.posonlyargs,
                    *node.args.args,
                    *node.args.kwonlyargs,
                ]
                for argument in arguments:
                    identifier = argument.arg
                    if identifier not in allowedIdentifiers and _hasInternalUnderscore(identifier):
                        invalidIdentifiers.append(f"{path.name}:{node.lineno}:{identifier}")
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in {"self", "cls"}
                and _hasInternalUnderscore(node.attr)
            ):
                invalidIdentifiers.append(f"{path.name}:{node.lineno}:{node.attr}")

    assert invalidIdentifiers == []
