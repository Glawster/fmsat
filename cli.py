"""Command line interface for the FMF reverse engineering toolkit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from organiseMyProjects.logUtils import getLogger, setApplication

thisApplication = "myHandbook"
setApplication(thisApplication)
logger = getLogger(includeConsole=False)

from fmsat.diff import filesDiff  # noqa: E402
from fmsat.parser import FMFParser, FMFTactic  # noqa: E402
from fmsat.report import diffReport, inspectionReport, structuresReport  # noqa: E402
from fmsat.signatures import asciiStrings  # noqa: E402
from fmsat.structuresDiscovery import structuresRepeated  # noqa: E402


def parserBuild() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fmsat")
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument(
        "-y",
        "--confirm",
        dest="confirm",
        action="store_true",
        help="execute changes (default is dry-run)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect = subparsers.add_parser("inspect", help="Inspect file signatures and sections")
    inspect.add_argument("file", type=Path)

    diff = subparsers.add_parser("diff", help="Compare two controlled tactic files")
    diff.add_argument("old", type=Path)
    diff.add_argument("new", type=Path)

    report = subparsers.add_parser("report", help="Generate a Markdown tactic report")
    report.add_argument("file", type=Path)

    dump = subparsers.add_parser("dump", help="Dump current parsed tactic model")
    dump.add_argument("file", type=Path)

    strings = subparsers.add_parser("strings", help="Extract printable ASCII strings")
    strings.add_argument("file", type=Path)
    strings.add_argument("--minimum", type=int, default=4)

    hexView = subparsers.add_parser("hex", help="Print a compact hex view")
    hexView.add_argument("file", type=Path)
    hexView.add_argument("--offset", type=int, default=0)
    hexView.add_argument("--length", type=int, default=256)

    structures = subparsers.add_parser("structures", help="Find repeated binary structures")
    structures.add_argument("file", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    global logger

    args = parserBuild().parse_args(argv)
    dryRun = not args.confirm
    logger = getLogger(includeConsole=args.verbose > 0, dryRun=dryRun)
    logger.doing("fmsat command")
    logger.value("command", args.command)
    logger.value("dryRun", dryRun)

    try:
        if args.command == "inspect":
            filePath = pathValidateFile(args.file)
            print(inspectionReport(FMFParser().inspect(filePath)), end="")
            logger.done("fmsat command")
            return 0
        if args.command == "diff":
            oldPath = pathValidateFile(args.old)
            newPath = pathValidateFile(args.new)
            print(diffReport(oldPath, newPath, filesDiff(oldPath, newPath)), end="")
            logger.done("fmsat command")
            return 0
        if args.command == "report":
            tactic = FMFTactic.read(pathValidateFile(args.file))
            print(_tacticReport(tactic), end="")
            logger.done("fmsat command")
            return 0
        if args.command == "dump":
            print(FMFTactic.read(pathValidateFile(args.file)))
            logger.done("fmsat command")
            return 0
        if args.command == "strings":
            filePath = pathValidateFile(args.file)
            for item in asciiStrings(filePath.read_bytes(), minimum=args.minimum):
                print(f"{item.offset}: {item.value}")
            logger.done("fmsat command")
            return 0
        if args.command == "hex":
            filePath = pathValidateFile(args.file)
            print(_hexFormat(filePath.read_bytes(), offset=args.offset, length=args.length), end="")
            logger.done("fmsat command")
            return 0
        if args.command == "structures":
            filePath = pathValidateFile(args.file)
            print(structuresReport(structuresRepeated(filePath.read_bytes())), end="")
            logger.done("fmsat command")
            return 0
    except Exception as error:
        logger.error("fmsat command failed: %s", error)
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 2


def pathValidateFile(filePath: Path) -> Path:
    """Resolve and validate an input file path before processing."""
    resolvedPath = filePath.expanduser().resolve()
    if not resolvedPath.is_file():
        raise FileNotFoundError(f"Input file does not exist: {resolvedPath}")
    return resolvedPath


def _hexFormat(data: bytes, *, offset: int, length: int) -> str:
    if offset < 0:
        raise ValueError("offset must be non-negative")
    if length < 0:
        raise ValueError("length must be non-negative")

    lines: list[str] = []
    stopOffset = min(len(data), offset + length)
    for rowOffset in range(offset, stopOffset, 16):
        row = data[rowOffset : min(rowOffset + 16, stopOffset)]
        hexBytes = " ".join(f"{byte:02x}" for byte in row)
        asciiBytes = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in row)
        lines.append(f"{rowOffset:08x}  {hexBytes:<47}  {asciiBytes}")
    return "\n".join(lines) + ("\n" if lines else "")


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


if __name__ == "__main__":
    sys.exit(main())
