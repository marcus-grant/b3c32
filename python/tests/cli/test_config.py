# python/tests/cli/test_config.py
"""Tests for the b3c32sum option table, parser, and Config.

Author: Marcus Grant
Date: 2026-09-14
License: Apache-2.0
"""

import dataclasses
from pathlib import Path

import pytest

from b3c32.cli.config import (
    DEFAULT_WIDTH_BITS,
    OPTIONS,
    Config,
    Stdin,
    UsageError,
    build_parser,
    parse,
)
from b3c32.digest import CERTIFIED_BITS


class TestBuildParser:
    def test_every_option_names_a_config_field(self) -> None:
        """Each row's field is a Config field; that lookup is what build_parser
        relies on for defaults, so a typo here must fail before argparse."""
        names = {f.name for f in dataclasses.fields(Config)}
        for opt in OPTIONS:
            assert opt.field in names, opt

    def test_default_width_is_certified(self) -> None:
        """DEFAULT_WIDTH_BITS in CERTIFIED_BITS, whatever the set becomes."""
        assert DEFAULT_WIDTH_BITS in CERTIFIED_BITS

    def test_bare_argv_matches_config_defaults(self) -> None:
        """build_parser().parse_args([]) yields, per option row, the same
        value as the Config field default. Positional default is "-"."""
        namespace = build_parser().parse_args([])
        defaults = {f.name: f.default for f in dataclasses.fields(Config)}
        assert namespace.path == "-"
        for opt in OPTIONS:
            assert getattr(namespace, opt.field) == defaults[opt.field]

    def test_no_progress_flag_clears_progress(self) -> None:
        """--no-progress stores False on namespace.progress."""
        assert build_parser().parse_args(["--no-progress"]).progress is False

    def test_total_parses_as_int(self) -> None:
        """-T/--total-bytes takes a byte count; the row's converter turns the
        string into an int so Config never sees text."""
        assert build_parser().parse_args(["-T", "5"]).total == 5


class TestParse:
    def test_path_builds_config(self, tmp_path: Path) -> None:
        """parse([str(p)]) == Config(source=p); every other field default."""
        assert parse([str(path := tmp_path / "f")]) == Config(source=path)

    def test_stdin_builds_config(self):
        """stdin or piped inputs lead to correct config build"""
        assert parse(["-"]) == parse([]) == Config(source=Stdin())

    def test_total_with_path_raises_usage_error(self, tmp_path: Path) -> None:
        """A file's size comes from stat; a supplied total would only
        disagree with it, so the pair is rejected before Config exists."""
        with pytest.raises(UsageError):
            parse([str(tmp_path / "f"), "-T", "5"])

    def test_total_with_stdin_builds_config(self) -> None:
        """Stdin has no size of its own, so a supplied total is the one
        place the option is meaningful."""
        assert parse(["-T", "5"]) == Config(source=Stdin(), total=5)
