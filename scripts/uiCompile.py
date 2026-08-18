#!/usr/bin/env python3
"""Compile Qt Designer `.ui` files into Python modules."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def uiFilesDiscover(uiDirectory: Path) -> list[Path]:
    """Return sorted `.ui` files directly beneath the Designer source directory."""

    return sorted(path for path in uiDirectory.glob("*.ui") if path.is_file())


def uiModuleGenerate(uiFile: Path, outputDirectory: Path, uicCommand: str) -> Path:
    """Compile one `.ui` file and return the generated Python path."""

    outputDirectory.mkdir(parents=True, exist_ok=True)
    outputFile = outputDirectory / f"ui_{uiFile.stem}.py"
    subprocess.run(
        [uicCommand, str(uiFile), "-o", str(outputFile)],
        check=True,
    )
    return outputFile


def uiCompile(
    projectRoot: Path,
    *,
    uicCommand: str = "pyside6-uic",
    checkOnly: bool = False,
) -> int:
    """Compile all Designer files or verify generated output is current."""

    uiDirectory = projectRoot / "app" / "ui"
    outputDirectory = uiDirectory / "generated"
    uiFiles = uiFilesDiscover(uiDirectory)
    if not uiFiles:
        print("No `.ui` files found under app/ui/")
        return 0

    staleFiles: list[Path] = []
    for uiFile in uiFiles:
        outputFile = outputDirectory / f"ui_{uiFile.stem}.py"
        if not outputFile.exists() or uiFile.stat().st_mtime > outputFile.stat().st_mtime:
            staleFiles.append(uiFile)

    if checkOnly:
        if staleFiles:
            names = ", ".join(path.name for path in staleFiles)
            print(f"Generated UI is stale for: {names}")
            print("Run: python scripts/uiCompile.py")
            return 1
        print("Generated UI is up to date.")
        return 0

    generated: list[Path] = []
    for uiFile in uiFiles:
        generated.append(uiModuleGenerate(uiFile, outputDirectory, uicCommand))

    print("Generated:")
    for path in generated:
        print(f"  {path.relative_to(projectRoot)}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root containing app/ui/",
    )
    parser.add_argument(
        "--uic",
        default="pyside6-uic",
        help="UIC executable to invoke",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when generated modules are missing or older than their `.ui` source",
    )
    args = parser.parse_args()
    sys.exit(
        uiCompile(
            args.project_root,
            uicCommand=args.uic,
            checkOnly=args.check,
        )
    )


if __name__ == "__main__":
    main()
