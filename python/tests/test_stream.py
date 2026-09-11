# python/tests/test_stream.py
"""
Tests for the streaming infrastructure: chunk loop wiring, progress
callback semantics, error propagation, and the stream and path
readers. No reference vectors here; certification is the digest
layer's, and each entry point gets one wiring test against the layer
below it.

Author: Marcus Grant
Date: 2026-09-11
License: Apache-2.0
"""

from collections.abc import Iterator

import pytest

from b3c32.digest import UncertifiedWidthError, _IncrementalDigest
from b3c32.stream import _ProgressReporter, digest_from_chunks
from tests.vectors import _chunked, _reference_input


def _clocked_reporter(
    interval_ms: int = 1000,
) -> tuple[_ProgressReporter, list[int], list[float]]:
    """A reporter on a hand-driven clock, with its seen-list and clock cell.

    Tests move time by assigning now[0]; every report lands in seen.
    """
    seen: list[int] = []
    now: list[float] = [0.0]  # mutable so the reporter can see it
    reporter = _ProgressReporter(seen.append, interval_ms, clock=lambda: now[0])
    return reporter, seen, now


class TestProgressReporter:
    """The reporter's policy, driven by a hand-advanced clock."""

    # bytes to advcance per call,
    ADV = 1023  # corresponding to a leaf minus one for chunking tests

    def test_start_reports_zero(self) -> None:
        """start fires the callback once with 0."""
        reporter, seen, _ = _clocked_reporter()
        reporter.start()
        assert seen == [0]

    def test_advance_never_reports(self) -> None:
        """After start's 0, two advance calls leave the callback untouched:
        advance counts bytes and never reports them itself."""
        reporter, seen, _ = _clocked_reporter()
        reporter.start()
        reporter.advance(self.ADV)
        reporter.advance(self.ADV)
        assert seen == [0]

    def test_maybe_report_suppressed_before_interval(self) -> None:
        """With the clock inside the interval, maybe_report stays silent."""
        reporter, seen, now = _clocked_reporter()
        reporter.start()
        reporter.maybe_report()
        reporter.advance(self.ADV)
        now[0] = 0.5
        reporter.maybe_report()
        assert seen == [0]

    def test_maybe_report_fires_once_interval_elapsed(self) -> None:
        """Once the clock passes the interval, maybe_report fires the running
        total, then falls silent again until another interval elapses."""
        reporter, seen, now = _clocked_reporter()
        reporter.start()
        reporter.advance(self.ADV)
        now[0] = 1.5
        reporter.maybe_report()
        assert seen == [0, self.ADV]
        reporter.advance(self.ADV)
        now[0] = 2.0
        reporter.maybe_report()
        assert seen == [0, self.ADV]

    def test_finish_reports_unreported_total(self) -> None:
        """finish fires the total when the last report was smaller."""
        reporter, seen, _ = _clocked_reporter()
        reporter.start()
        reporter.advance(self.ADV)
        reporter.finish()
        assert seen == [0, self.ADV]

    def test_finish_skips_when_total_already_reported(self) -> None:
        """finish is silent when the total was the last value reported."""
        reporter, seen, now = _clocked_reporter()
        reporter.start()
        reporter.advance(self.ADV)
        now[0] = 1.5
        reporter.maybe_report()
        reporter.finish()
        assert seen == [0, self.ADV]

    def test_none_callback_is_noop(self) -> None:
        """Every event runs without a callback and nothing raises."""
        reporter, _, _ = _clocked_reporter()
        reporter.start()
        reporter.advance(self.ADV)
        reporter.maybe_report()
        reporter.finish()

    def test_start_twice_raises(self) -> None:
        """A second start is a caller bug and fails loudly."""
        reporter, _, _ = _clocked_reporter()
        reporter.start()
        with pytest.raises(RuntimeError):
            reporter.start()


WIDTH = 120  # Only currently certified digest width, in bits
LEAF_MINUS1 = 1023  # Blake3 leaf size minus one, for chunking tests
REFERENCE_SIZE = 2049  # Size of the reference input, in bytes
DATA = _reference_input(REFERENCE_SIZE)  # Standard test input, covers multiple leaves
CHUNKS = _chunked(DATA, LEAF_MINUS1)  # Split into chunks for streaming tests


class Boom(Exception):
    """Custom Exception class for marking a raised exception in tests."""


class TestDigestFromChunks:
    """The chunk loop drives the primitive and owns progress."""

    def test_wiring_matches_primitive(self) -> None:
        """Chunks fed through the loop equal the primitive fed directly."""
        expected = _IncrementalDigest().update(DATA).digest(WIDTH)
        assert digest_from_chunks(CHUNKS, WIDTH) == expected

    def test_progress_starts_at_zero_ends_at_total(self) -> None:
        """First call is 0, last call is the byte total."""
        seen: list[int] = []
        digest_from_chunks(CHUNKS, WIDTH, on_progress=seen.append)
        assert seen[0] == 0
        assert seen[-1] == len(DATA)

    def test_progress_on_empty_input_is_zero(self) -> None:
        """Empty input still reports; every value seen is 0."""
        seen: list[int] = []
        digest_from_chunks([], WIDTH, on_progress=seen.append)
        assert len(seen) >= 1
        assert all(n == 0 for n in seen)

    def test_progress_is_cumulative_and_monotonic(self) -> None:
        """With interval 0 every chunk reports, values never decrease."""
        seen: list[int] = []
        digest_from_chunks(CHUNKS, WIDTH, on_progress=seen.append, interval_ms=0)
        assert seen == [0, LEAF_MINUS1, LEAF_MINUS1 * 2, REFERENCE_SIZE]

    def test_iterable_error_propagates_without_digest(self) -> None:
        """An exception mid-iteration propagates; nothing is returned."""

        def chunks() -> Iterator[bytes]:
            yield CHUNKS[0]  # tick
            yield CHUNKS[1]  # tick
            raise Boom  # BOOM!

        seen: list[int] = []
        with pytest.raises(Boom):
            digest_from_chunks(chunks(), WIDTH, on_progress=seen.append, interval_ms=0)
        assert seen == [0, LEAF_MINUS1, 2 * LEAF_MINUS1]

    def test_callback_error_propagates(self) -> None:
        """A raising callback aborts the hash with its own exception."""

        def boom(_: int) -> None:
            raise Boom

        with pytest.raises(Boom):
            digest_from_chunks(CHUNKS, WIDTH, on_progress=boom, interval_ms=0)

    def test_uncertified_width_raises(self) -> None:
        """The hashing primitive's width check is reached through the loop."""
        with pytest.raises(UncertifiedWidthError):
            digest_from_chunks(CHUNKS, 123)
