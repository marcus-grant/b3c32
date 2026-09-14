# python/src/b3c32/cli/progress.py
"""Progress bar and status line for b3c32sum, stderr only.

Rendering is pure; draw is the on_progress callback and the one place
that reads the clock and writes.

Author: Marcus Grant
Date: 2026-09-14
License: Apache-2.0
"""

import time
from dataclasses import dataclass
from typing import TextIO

BAR_WIDTH = 25
MIB = 1 << 20


@dataclass
class Drawn:
    """Frame counter shared between draw and sum_command.

    draw increments it per bar frame written; sum_command reads it
    after hashing to decide whether a status line is owed. Mutable on
    purpose: the callback has no return channel.
    """

    frames: int = 0
    bytes: int = 0


def render_bar(done: int, total: int, width: int, elapsed_s: float) -> str:
    """Render one in-place progress frame.

    Args:
        done: Bytes hashed so far; must be strictly between 0 and total.
        total: Size of the input in bytes.
        width: Number of cells between the brackets.
        elapsed_s: Seconds since hashing started.

    Returns:
        A carriage return, the bar, the floored percentage, done and
        total in MiB, and the estimated seconds remaining at the
        average rate so far. No trailing newline, so the next frame
        overwrites this one.
    """
    filled = done * width // total
    cells = "#" * filled + "-" * (width - filled)
    pct = done * 100 // total
    left = round(elapsed_s * (total - done) / done)
    fmt_done, fmt_tot = done / MIB, total / MIB
    return f"\r[{cells}] {pct}% {fmt_done:.1f}/{fmt_tot:.1f} MiB {left}s left"


def render_status(path: str, total: int, elapsed_s: float) -> str:
    """Render the permanent summary line written after the bar.

    Args:
        path: The input as the user named it.
        total: Bytes hashed.
        elapsed_s: Seconds the hash took; must be positive.

    Returns:
        Carriage return plus erase-to-end-of-line, then path, size in
        MiB, elapsed seconds, and average MiB/s, ending in a newline.
    """
    total_mib = total / MIB
    return (
        f"\r\x1b[K{path} {total_mib:.1f} MiB in {elapsed_s:.1f}s, "
        f"{total_mib / elapsed_s:.1f} MiB/s\n"
    )


def render_count(done: int, elapsed_s: float) -> str:
    """Render one in-place frame for a source of unknown size.

    Args:
        done: Bytes hashed so far; must be positive.
        elapsed_s: Seconds since hashing started.

    Returns:
        A carriage return, done in MiB, and the average MiB/s so far.
        No trailing newline, so the next frame overwrites this one.
    """
    done_mib = done / MIB
    return f"\r{done_mib:.1f} MiB {done_mib / elapsed_s:.1f} MiB/s"


def draw(
    done: int, *, total: int | None, err: TextIO, started: float, drawn: Drawn
) -> None:
    """The on_progress callback sum_command binds with functools.partial.

    The library passes only bytes consumed; everything else is bound.
    The report at 0 is the library's unconditional start call and
    produces no output. With a total, the report at total is likewise
    the finish call and is skipped, and the frame is a bar. Without a
    total the finish call is indistinguishable from progress, so every
    later report draws a count frame. Either way drawn.bytes records
    the latest report and drawn.frames counts frames written. This is
    the only clock read in the module.

    Args:
        done: Cumulative bytes consumed, from the library.
        total: Size of the input in bytes, or None when unknown.
        err: Where frames go; stderr in production, a StringIO in tests.
        started: time.monotonic() reading taken before the hash call.
        drawn: Frame counter shared with sum_command.
    """
    if done == 0:
        return
    drawn.bytes = done
    elapsed_s = time.monotonic() - started
    if total is None:
        frame = render_count(done, elapsed_s)
    elif done == total:
        return
    else:
        frame = render_bar(done, total, BAR_WIDTH, elapsed_s)
    err.write(frame)
    err.flush()
    drawn.frames += 1
