"""Command line interface for the FMF reverse engineering toolkit."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from organiseMyProjects.logUtils import getLogger, setLogLevel

logger = getLogger()

from fmparser.bundleFilter import assetsFilter  # noqa: E402
from fmparser.bundles import BundleError, UnityPyBundleReader  # noqa: E402
from fmparser.config import tacticDefaultGet, tacticDefaultSet  # noqa: E402
from fmparser.diff import diff_files  # noqa: E402
from fmparser.parser import FMFTactic, FMFParser  # noqa: E402
from fmparser.report import diff_report, inspection_report  # noqa: E402
from fmparser.structures import AssetData, AssetInfo, BundleInfo  # noqa: E402


def buildParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fmparser")
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument(
        "-y",
        "--confirm",
        dest="confirm",
        action="store_true",
        help="execute changes (default is dry-run)",
    )
    parser.add_argument("--tactic", type=Path, help="FM tactic file to use")
    parser.add_argument("--inspect", action="store_true", help="Inspect the selected tactic file")
    parser.add_argument(
        "--print",
        dest="print_tactic",
        action="store_true",
        help="Print the parsed tactic model report",
    )
    parser.add_argument("--compare", type=Path, help="Compare selected tactic against another tactic")
    parser.add_argument("--save", action="store_true", help="Store --tactic as the default tactic")
    parser.add_argument("--unity", type=Path, help="Unity bundle file to inspect")
    parser.add_argument("--list", action="store_true", help="List assets in the selected Unity bundle")
    parser.add_argument("--preview", type=int, help="Preview a Unity bundle asset by path ID")
    parser.add_argument("--gui", action="store_true", help="Launch the Qt Unity bundle explorer")
    parser.add_argument("--filter", default="", help="Filter bundle assets by name, type, container, or path ID")
    parser.add_argument("--type", default="", help="Filter bundle assets by Unity object type")
    parser.add_argument("--limit", type=int, default=100, help="Maximum bundle assets to print")

    return parser


def main(argv: list[str] | None = None) -> int:
    global logger

    parser = buildParser()
    args = parser.parse_args(argv)
    dryRun = not args.confirm
    logger = getLogger(includeConsole=args.verbose > 0, dryRun=dryRun)
    logger.doing("fmparser command")
    logger.value("dryRun", dryRun)

    try:
        if not _hasTacticAction(args) and not _hasUnityAction(args):
            parser.print_help()
            return 2
        if _hasTacticAction(args) and _hasUnityAction(args):
            raise ValueError("Choose either tactic options or Unity options, not both.")
        if _hasTacticAction(args):
            return _tacticActionRun(args)
        if _hasUnityAction(args):
            return _unityActionRun(args)
    except BundleError as error:
        logger.error("bundle command failed: %s", error)
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        logger.error("fmsat command failed: %s", error)
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 2


def configTacticResolve(tacticPath: Path | None) -> Path:
    """Resolve a tactic path from CLI input or user config."""

    selectedPath = tacticPath or tacticDefaultGet()
    if selectedPath is None:
        raise FileNotFoundError(
            "No tactic file supplied. Use --tactic PATH or store one with "
            "--tactic PATH --save."
        )
    return pathValidateFile(selectedPath)


def pathValidateFile(filePath: Path) -> Path:
    """Resolve and validate an input file path before processing."""
    resolvedPath = filePath.expanduser().resolve()
    if not resolvedPath.is_file():
        raise FileNotFoundError(f"Input file does not exist: {resolvedPath}")
    return resolvedPath


def _hasTacticAction(args: argparse.Namespace) -> bool:
    return bool(args.inspect or args.print_tactic or args.compare or args.save or args.tactic)


def _hasUnityAction(args: argparse.Namespace) -> bool:
    return bool(args.unity or args.list or args.preview is not None or args.gui)


def _tacticActionRun(args: argparse.Namespace) -> int:
    tacticPath = configTacticResolve(args.tactic)

    actions = [args.inspect, args.print_tactic, args.compare is not None]
    actionCount = sum(1 for action in actions if action)
    if actionCount == 0 and args.tactic is not None:
        configPath = tacticDefaultSet(tacticPath)
        logger.value("config", configPath)
        print(f"Default tactic: {tacticPath}\n")
        logger.done("fmparser command")
        return 0
    if args.save:
        if args.tactic is None:
            raise ValueError("--save requires --tactic PATH.")
        configPath = tacticDefaultSet(tacticPath)
        logger.value("config", configPath)
    if actionCount != 1:
        raise ValueError("Choose exactly one tactic action: --inspect, --print, or --compare PATH.")

    if args.inspect:
        print(inspection_report(FMFParser().inspect(tacticPath)), end="")
    elif args.print_tactic:
        print(_tacticReport(FMFTactic.read(tacticPath)), end="")
    elif args.compare:
        comparePath = pathValidateFile(args.compare)
        print(diff_report(tacticPath, comparePath, diff_files(tacticPath, comparePath)), end="")
    logger.done("fmparser command")
    return 0


def _unityActionRun(args: argparse.Namespace) -> int:
    actions = [args.list, args.preview is not None, args.gui]
    if sum(1 for action in actions if action) != 1:
        raise ValueError("Choose exactly one Unity action: --list, --preview PATH_ID, or --gui.")
    if args.unity is None and not args.gui:
        raise FileNotFoundError("No Unity bundle supplied. Use --unity PATH.")
    if args.gui:
        from fmparser.qtBundleExplorer import main as qt_main

        return qt_main([str(args.unity)] if args.unity else [])

    bundlePath = pathValidateFile(args.unity)
    reader = UnityPyBundleReader()
    info = reader.open(bundlePath)
    if args.list:
        assets = assetsFilter(reader.assetsList(), text=args.filter, asset_type=args.type)
        print(_bundleListReport(info, assets[: max(0, args.limit)]), end="")
    elif args.preview is not None:
        print(_assetDataReport(reader.assetRead(args.preview)), end="")
    logger.done("fmparser command")
    return 0


def _tacticReport(tactic: FMFTactic) -> str:
    lines = [
        "Formation",
        "---------",
        tactic.formation or "unknown",
        "",
        "Mentality",
        "---------",
        tactic.mentality or "unknown",
        "",
        "Roles",
        "-----",
    ]
    if tactic.players:
        lines.extend(
            f"{player.position}: {player.role or 'unknown'} ({player.duty or 'unknown'})"
            for player in tactic.players
        )
    else:
        lines.append("unknown")
    lines.extend(["", "Instructions", "------------"])
    lines.extend(tactic.teamInstructions or ["unknown"])
    return "\n".join(lines) + "\n"


def _bundleListReport(info: BundleInfo, assets: tuple[AssetInfo, ...]) -> str:
    lines = [
        "Bundle",
        "------",
        f"Filename: {info.file_name}",
        f"Path: {info.path}",
        f"Size: {info.size}",
        f"Signature: {info.signature}",
        f"Unity version: {info.unity_version or 'unknown'}",
        f"Asset count: {info.asset_count}",
        "",
        "Assets",
        "------",
    ]
    if not assets:
        lines.append("- none")
    for asset in assets:
        lines.append(
            f"- {asset.path_id}: {asset.asset_name or '(unnamed)'} "
            f"[{asset.asset_type}] container={asset.container_path or 'unknown'} "
            f"size={asset.serialized_size if asset.serialized_size is not None else 'unknown'} "
            f"refs={len(asset.dependencies) + len(asset.external_references)}"
        )
    return "\n".join(lines) + "\n"


def _assetDataReport(data: AssetData) -> str:
    lines = [
        "Asset",
        "-----",
        f"Path ID: {data.asset.path_id}",
        f"Name: {data.asset.asset_name or 'unknown'}",
        f"Type: {data.asset.asset_type}",
        f"Container: {data.asset.container_path or 'unknown'}",
        f"Representation: {data.representation}",
    ]
    if data.message:
        lines.extend(["", "Note", "----", data.message])
    if data.text:
        lines.extend(["", "Preview", "-------", data.text])
    elif not data.message:
        lines.extend(["", "Preview", "-------", "No readable preview is available."])
    return "\n".join(lines) + "\n"


def _bundleListReport(info: BundleInfo, assets: tuple[AssetInfo, ...]) -> str:
    lines = [
        "Bundle",
        "------",
        f"Filename: {info.file_name}",
        f"Path: {info.path}",
        f"Size: {info.size}",
        f"Signature: {info.signature}",
        f"Unity version: {info.unity_version or 'unknown'}",
        f"Asset count: {info.asset_count}",
        "",
        "Assets",
        "------",
    ]
    if not assets:
        lines.append("- none")
    for asset in assets:
        lines.append(
            f"- {asset.path_id}: {asset.asset_name or '(unnamed)'} "
            f"[{asset.asset_type}] container={asset.container_path or 'unknown'} "
            f"size={asset.serialized_size if asset.serialized_size is not None else 'unknown'} "
            f"refs={len(asset.dependencies) + len(asset.external_references)}"
        )
    return "\n".join(lines) + "\n"


def _assetDataReport(data: AssetData) -> str:
    lines = [
        "Asset",
        "-----",
        f"Path ID: {data.asset.path_id}",
        f"Name: {data.asset.asset_name or 'unknown'}",
        f"Type: {data.asset.asset_type}",
        f"Container: {data.asset.container_path or 'unknown'}",
        f"Representation: {data.representation}",
    ]
    if data.message:
        lines.extend(["", "Note", "----", data.message])
    if data.text:
        lines.extend(["", "Preview", "-------", data.text])
    elif not data.message:
        lines.extend(["", "Preview", "-------", "No readable preview is available."])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
