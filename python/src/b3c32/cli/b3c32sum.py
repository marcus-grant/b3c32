# python/src/b3c32/cli/b3c32sum.py
"""Console entry point for b3c32sum.

Author: Marcus Grant
Date: 2026-09-14
License: Apache-2.0
"""

import sys
from typing import assert_never

from .config import PROG_NAME, UsageError, parse
from .sum import sum_command


def main(
    argv: list[str] | None = None, *, interval_ms: int = 1000, read_size: int = 1 << 20
) -> int:
    """Parse argv, run the operation it names, return its exit code.

    Never calls sys.exit; the console_scripts wrapper does that with the
    return value. argparse's own SystemExit propagates untouched.

    Args:
        argv: Arguments after the program name; None means sys.argv[1:].
        interval_ms: Forwarded to the handler; tests pass 0.
        read_size: Forwarded to the handler; tests pass something tiny.

    Returns:
        The handler's exit code, or 2 after writing
        "b3c32sum: <message>" to stderr for a UsageError.
    """
    try:
        cfg = parse(argv)
    except UsageError as e:
        sys.stderr.write(f"{PROG_NAME}: {e}\n")
        return 2
    if cfg.operation == "sum":
        return sum_command(cfg, interval_ms=interval_ms, read_size=read_size)
    assert_never(cfg.operation)
