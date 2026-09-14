# python/tests/cli/test_progress.py
"""Tests for the b3c32sum progress renderers and the draw callback.

Author: Marcus Grant
Date: 2026-09-14
License: Apache-2.0
"""

import io
import time

from b3c32.cli.progress import Drawn, _draw, render_bar, render_status

MIB = 1 << 20


class TestRenderBar:
    def test_example(self) -> None:
        """A mid-stream frame carries everything a human reads off a
        progress bar: the bar, percent, over total in MiB,
        and estimate of time left from the average rate."""
        frame = render_bar(4 * MIB, 10 * MIB, 10, 2.0)
        assert frame == "\r[####------] 40% 4.0/10.0 MiB 3s left"

    def test_floors(self) -> None:
        """Cells & percent floor, bars that round-up show
        full bar or 100% while bytes remain.
        The final report is never drawn, so last frame seen must be honest."""
        frame = render_bar(99, 100, 10, 1.0)
        assert frame.startswith("\r[#########-] 99%")


class TestRenderStatus:
    def test_example(self) -> None:
        """Closing line clears bar & leaves permanent summary:
        path, size in MiB, elapsed seconds, & average throughput.
        Ends with newline so the next stderr write starts clean."""
        line = render_status("f", 10 * MIB, 4.0)
        assert line == "\r\x1b[Kf 10.0 MiB in 4.0s, 2.5 MiB/s\n"


class TestDraw:
    def test_skips_start_and_total(self) -> None:
        """Library reports on start & finish unconditionally. Neither is progress;
        a job under one interval gets exactly those two should gen no stderr &
        no frame count."""
        err, drawn, started = io.StringIO(), Drawn(), time.monotonic()
        _draw(0, total=10, err=err, started=started, drawn=drawn)
        _draw(10, total=10, err=err, started=started, drawn=drawn)
        assert err.getvalue() == ""
        assert drawn.frames == 0

    def test_writes_frame_and_counts(self) -> None:
        """Reports between start & finish write one frame to stream.
        Then bumps frame count that sum_command reads to decide if status line is owed.
        The clock is read inside _draw, only static parts of the frame are checked."""
        err, drawn, started = io.StringIO(), Drawn(), time.monotonic()
        _draw(4, total=10, err=err, started=started, drawn=drawn)
        frame = err.getvalue()
        assert frame.startswith("\r[") and "MiB" in frame
        assert not frame.endswith("\n")
        assert drawn.frames == 1
