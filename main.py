"""Top-level command dispatcher for FMSAT."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Launch the desktop application or dispatch a named CLI command."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        from fmsat.app.main import main as appMain

        return appMain()

    if arguments[0] == "parser":
        from fmsat.cli import main as parserMain

        return parserMain(arguments[1:])

    if arguments[0] in {"-h", "--help"}:
        print(
            "usage: fmsat [parser ...]\n\n"
            "Run without arguments to launch the desktop application.\n\n"
            "commands:\n"
            "  parser    Inspect and compare Football Manager .fmf files\n\n"
            "Run 'fmsat parser --help' for parser command help."
        )
        return 0

    print(f"fmsat: error: unknown command: {arguments[0]}", file=sys.stderr)
    print("Run 'fmsat --help' for usage.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
