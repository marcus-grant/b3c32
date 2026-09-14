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
from typing import BinaryIO

from b3c32 import code_from_stream

from .config import PROG_NAME, Config
from .progress import Drawn, draw, render_status


def _sum_stream(
    stream: BinaryIO,
    cfg: Config,
    *,
    total: int | None,
    label: str,
    interval_ms: int,
    read_size: int,
) -> str:
    """Hash one open binary stream with progress on stderr and return the code.

    The branch that opened the stream supplies what only it knows: the
    size, or None when unknown, and the label the status line names the
    source by. When cfg.progress is set, draw is bound over that size,
    sys.stderr, the start time, and a fresh Drawn; a status line follows
    the hash only if a frame was drawn, sized by the bytes draw recorded.
    Does not close the stream. OSError from a read propagates.

    Args:
        stream: Open for reading bytes; a file or sys.stdin.buffer.
        cfg: Supplies width_bits and progress.
        total: Size in bytes, or None to draw counts instead of a bar.
        label: How the status line names the source.
        interval_ms: Minimum spacing between progress reports.
        read_size: Bytes per stream read.
    """
    started, drawn = time.monotonic(), Drawn()
    on_progress = (
        functools.partial(
            draw, total=total, err=sys.stderr, started=started, drawn=drawn
        )
        if cfg.progress
        else None
    )
    code = code_from_stream(
        stream,
        cfg.width_bits,
        read_size=read_size,
        on_progress=on_progress,
        interval_ms=interval_ms,
    )
    if drawn.frames:
        sys.stderr.write(render_status(label, drawn.bytes, time.monotonic() - started))
    return code


def _sum_path(path: Path, cfg: Config, interval_ms: int, read_size: int) -> str:
    """Hash the file at path and return the code.

    The size comes from stat, so frames are bars and the finish report
    is recognised. OSError from stat, open, or read propagates.
    """
    total = path.stat().st_size
    with path.open("rb") as f:
        return _sum_stream(
            f,
            cfg,
            total=total,
            label=str(path),
            interval_ms=interval_ms,
            read_size=read_size,
        )


def _sum_stdin(cfg: Config, interval_ms: int, read_size: int) -> str:
    """Hash sys.stdin.buffer to exhaustion and return the code.

    The size is cfg.total, None unless --total-bytes was given: bars with it,
    running counts without. OSError from a read propagates.
    """
    return _sum_stream(
        sys.stdin.buffer,
        cfg,
        total=cfg.total,
        label="-",
        interval_ms=interval_ms,
        read_size=read_size,
    )


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
    label = str(cfg.source) if isinstance(cfg.source, Path) else "-"
    try:
        if isinstance(cfg.source, Path):
            code = _sum_path(cfg.source, cfg, interval_ms, read_size)
        else:
            code = _sum_stdin(cfg, interval_ms, read_size)
    except OSError as e:
        sys.stderr.write(f"{PROG_NAME}: {label}: {e.strerror}\n")
        return 3
    print(code)
    return 0
