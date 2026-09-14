# python/tests/cli/test_b3c32sum.py
"""Tests for the b3c32sum entry point: main and the console script.

Author: Marcus Grant
Date: 2026-09-14
License: Apache-2.0
"""

import io
from importlib.metadata import entry_points
from pathlib import Path

import pytest

from b3c32 import code_from_path
from b3c32.cli.b3c32sum import main
from b3c32.cli.config import Config, UsageError
from tests.vectors import REFERENCE_ENCODED_VECTORS, reference_input


class TestMain:
    def test_path_prints_code(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Command line to code on stdout, through parse and sum_command.
        --no-progress keeps stderr empty so the wiring is all that is
        under test."""
        (path := tmp_path / "f").write_bytes(b"hello")
        exit_code = main([str(path), "--no-progress"], interval_ms=0, read_size=2)
        out, err = capsys.readouterr()
        assert exit_code == 0
        assert out == code_from_path(str(path), 120) + "\n"
        assert err == ""

    def test_usage_error_returns_2(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Any UsageError out of parse becomes "b3c32sum: <message>" on
        stderr and exit 2, before any handler runs. parse is replaced so
        the test does not depend on which command lines are rejected."""

        def reject(argv: list[str] | None) -> Config:
            raise UsageError("boom")

        monkeypatch.setattr("b3c32.cli.b3c32sum.parse", reject)
        assert main([]) == 2
        out, err = capsys.readouterr()
        assert out == ""
        assert err == "b3c32sum: boom\n"

    def test_unknown_flag_exits_via_argparse(self) -> None:
        """argparse handles its own errors: usage text on stderr and
        SystemExit(2). main lets that propagate rather than translating
        it, so the exit code is argparse's."""
        with pytest.raises(SystemExit) as info:
            main(["--foobar"])
        assert info.value.code == 2


def test_console_script_loads_main() -> None:
    """The installed console_scripts entry named b3c32sum resolves to
    this main, so the wheel and the tested function cannot diverge."""
    (script,) = entry_points(group="console_scripts", name="b3c32sum")
    assert script.load() is main


@pytest.mark.e2e
def test_reference_2049_by_path_and_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The whole command at its defaults, once with the reference file as
    a path and once piped, both printing the frozen 2049 code. This is
    wiring against a regression pin, not certification: the code was
    frozen by the suite, and here it only proves the CLI reaches it."""
    data = reference_input(2049)
    expected = dict(REFERENCE_ENCODED_VECTORS)[2049] + "\n"
    (path := tmp_path / "ref").write_bytes(data)
    assert main([str(path)]) == 0
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(data)))
    assert main([]) == 0
    out, _ = capsys.readouterr()
    assert out == expected * 2
