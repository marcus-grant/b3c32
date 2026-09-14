# python/tests/cli/test_sum.py
"""Tests for the b3c32sum sum handler, as wiring over code_from_stream.

Author: Marcus Grant
Date: 2026-09-14
License: Apache-2.0
"""

import errno
import io
import os
from pathlib import Path

import pytest

from b3c32 import code_from_chunks, code_from_path
from b3c32.cli.config import DEFAULT_WIDTH_BITS, Config, Stdin
from b3c32.cli.sum import sum_command


class TestSumCommand:
    def test_prints_code_alone(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Default display is code & newline on stdout, nothing else;
         with progress off, stderr stays empty.
        Expected code comes from the library on the same file:
        this checks adapter forwards correct width, not hash itself."""
        (path := tmp_path / "f").write_bytes(b"hello")
        cfg = Config(source=path, progress=False)
        assert sum_command(cfg) == 0
        out, err = capsys.readouterr()
        assert out == code_from_path(path, cfg.width_bits) + "\n"
        assert err == ""

    def test_draws_bar_then_status(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A five-byte file reads 2bytes chunks @ interval 0 reports 0, 2, 4, 5:
        two frames, then one status line ending in a newline. Stdout is unaffected."""
        (path := tmp_path / "f").write_bytes(b"hello")
        cfg = Config(source=path, progress=True)
        assert sum_command(cfg, interval_ms=0, read_size=2) == 0
        out, err = capsys.readouterr()
        assert out == code_from_path(path, cfg.width_bits) + "\n"
        assert err.count("\r[") == 2
        assert err.count("\x1b[K") == 1
        assert err.endswith("MiB/s\n")

    def test_no_progress_suppresses_stderr(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Same file and read size as above with progress off: no
        callback is bound, so no frames and no status line."""
        (path := tmp_path / "f").write_bytes(b"hello")
        cfg = Config(source=path, progress=False)
        assert sum_command(cfg, interval_ms=0, read_size=2) == 0
        out, err = capsys.readouterr()
        assert out == code_from_path(path, cfg.width_bits) + "\n"
        assert err == ""

    def test_unreadable_path_returns_3(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A missing file yields "b3c32sum: PATH: <strerror>" on stderr,
        nothing on stdout, and exit code 3. strerror comes from
        os.strerror(errno.ENOENT) so the text is not hardcoded."""
        cfg = Config(source=(path := tmp_path / "missing"), progress=False)
        assert sum_command(cfg) == 3
        out, err = capsys.readouterr()
        assert out == ""
        assert err == f"b3c32sum: {path}: {os.strerror(errno.ENOENT)}\n"


class TestSumStdin:
    def test_prints_code_alone(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A Stdin source reads sys.stdin.buffer to exhaustion and prints
        the code exactly as a path would; no bar, since stdin has no
        size, and nothing on stderr."""
        monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"hello")))
        assert sum_command(Config(source=Stdin())) == 0
        out, err = capsys.readouterr()
        assert out == code_from_chunks([b"hello"], DEFAULT_WIDTH_BITS) + "\n"
        assert err == ""
