# python/src/b3c32/cli/config.py
"""Option table, parser, and the Config every b3c32sum handler runs on.

Author: Marcus Grant
Date: 2026-09-14
License: Apache-2.0
"""

import argparse
import dataclasses
from collections.abc import Callable
from pathlib import Path
from typing import Literal

PROG_NAME = "b3c32sum"
DEFAULT_WIDTH_BITS = 120

Operation = Literal["sum"]
Display = Literal["code"]


class UsageError(Exception):
    """Invalid or unsupported command line; main prints it and returns 2."""


@dataclasses.dataclass(frozen=True)
class Stdin:
    """Marker source: read standard input. Not implemented this PR."""


@dataclasses.dataclass(frozen=True)
class Config:
    """Validated, fully materialised command; fields default to the bare
    command line so tests override only what they assert on."""

    source: Path | Stdin
    operation: Operation = "sum"
    display: Display = "code"
    progress: bool = True
    width_bits: int = DEFAULT_WIDTH_BITS
    total: int | None = None


@dataclasses.dataclass(frozen=True)
class Option:
    """One flag row. field names the Config field it feeds and is passed
    to argparse as dest; the default is read from that field."""

    flags: tuple[str, ...]
    field: str
    help: str
    parse: Callable[[str], object] | None = None


OPTIONS: tuple[Option, ...] = (
    Option(("--no-progress",), "progress", "suppress the stderr progress bar"),
    Option(
        ("-T", "--total-bytes"), "total", "expected size in bytes, draws a bar on stdin", int
    ),
)


def build_parser() -> argparse.ArgumentParser:
    """Positional path (nargs "?", default "-") plus one add_argument per
    OPTIONS row; bool default True is store_false, False is store_true."""
    defaults = {f.name: f.default for f in dataclasses.fields(Config)}
    p = argparse.ArgumentParser(prog=PROG_NAME)
    p.add_argument("path", nargs="?", default="-")
    for opt in OPTIONS:
        if opt.parse is not None:
            p.add_argument(
                *opt.flags,
                dest=opt.field,
                type=opt.parse,
                default=defaults[opt.field],
                help=opt.help,
            )
        else:
            action = "store_false" if defaults[opt.field] else "store_true"
            p.add_argument(*opt.flags, dest=opt.field, action=action, help=opt.help)
    return p


def validate(namespace: argparse.Namespace) -> None:
    """Reject command lines whose fields conflict, before Config exists.

    Every cross-field rule lives here so each new operation or option
    adds its rule in one place with one test. Current rules:
    --total-bytes with a path, since a file's size comes from stat and a
    supplied total could only disagree with it.

    Raises:
        UsageError: naming the conflict; main prints it and returns 2.
    """
    if namespace.total is not None and namespace.path != "-":
        raise UsageError("total is only for stdin")


def parse(argv: list[str] | None) -> Config:
    """build_parser, parse_args(argv), validate, then Config. argparse's
    own SystemExit propagates."""
    namespace = build_parser().parse_args(argv)
    validate(namespace)
    path = Path(namespace.path) if namespace.path != "-" else Stdin()
    overrides = {opt.field: getattr(namespace, opt.field) for opt in OPTIONS}
    return Config(source=path, **overrides)
