"""Run FMParser as a package with ``python -m fmparser``."""

from __future__ import annotations

import sys

from fmparser.cli import main


if __name__ == "__main__":
    sys.exit(main())
