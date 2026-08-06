"""Run FMSAT as a package with ``python -m fmsat``."""

from __future__ import annotations

import sys

from fmsat.cli import main


if __name__ == "__main__":
    sys.exit(main())
