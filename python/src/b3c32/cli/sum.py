# python/src/b3c32/cli/sum.py
"""The sum operation of b3c32sum: hash one source, print its code.

Author: Marcus Grant
Date: 2026-09-14
License: Apache-2.0
"""

import functools
import sys
import time
from pathlib import Path

from b3c32 import code_from_stream

from .config import PROG_NAME, Config
from .progress import Drawn, draw, render_status


def _sum_path(path: Path, cfg: Config, interval_ms: int, read_size: int) -> str:
    """Helper to sum_command for its path branch of the command"""
    total = path.stat().st_size
    started = time.monotonic()
    drawn = Drawn()
    on_progress = None
    if cfg.progress:
        on_progress = functools.partial(
            draw,
            total=path.stat().st_size,
            err=sys.stderr,
            started=time.monotonic(),
            drawn=drawn,
        )
    else:
        on_progress = None
    with path.open("rb") as f:
        code = code_from_stream(
            f,
            cfg.width_bits,
            read_size=read_size,
            on_progress=on_progress,
            interval_ms=interval_ms,
        )
    if drawn.frames:
        status = render_status(str(path), total, time.monotonic() - started)
        sys.stderr.write(status)
    return code


def sum_command(
    cfg: Config,
    *,
    interval_ms: int = 1000,
    read_size: int = 1 << 20,
) -> int:
    """Hash config.source and print the code alone on stdout.

    Progress goes to stderr when config.progress is set: _draw is bound
    with the file size, sys.stderr, the start time, and a fresh Drawn,
    and a status line follows the hash only if a frame was drawn.
    interval_ms and read_size are forwarded to code_from_stream; tests
    lower them so a tiny file exercises the draw path.

    Args:
        config: A validated Config; a Stdin source raises
            NotImplementedError since parse rejects it first.
        interval_ms: Minimum spacing between progress reports.
        read_size: Bytes per stream read.

    Returns:
        0 on success; 3 when the source cannot be opened or read, after
        writing "b3c32sum: PATH: <strerror>" to stderr.
    """
    if isinstance(cfg.source, Path):
        try:
            code = _sum_path(cfg.source, cfg, interval_ms, read_size)
        except OSError as e:
            sys.stderr.write(f"{PROG_NAME}: {cfg.source}: {e.strerror}\n")
            return 3
        print(code)
        return 0
    return 1
