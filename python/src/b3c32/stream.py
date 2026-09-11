# python/src/b3c32/stream.py
"""
Streaming infrastructure over the digest primitive: a chunk loop with
progress reporting, and readers that adapt file objects and paths to
it. Nothing here touches blake3; every digest comes from
_IncrementalDigest, so certification is the digest layer's and this
module is proven by its loop and callback semantics plus one wiring
test per entry point.

Author: Marcus Grant
Date: 2026-09-11
License: Apache-2.0
"""

import time
from collections.abc import Callable, Iterable

from b3c32.digest import _IncrementalDigest

ProgressCallback = Callable[[int], None]
OptionalCallback = ProgressCallback | None
Clock = Callable[[], float]  # monotonic time in seconds


class _ProgressReporter:
    """Decides when to call the progress callback and remembers what it did.

    Reports cumulative bytes consumed: 0 at start, then at most once
    per interval as chunks advance, and at finish unless the last
    report already was the total. All progress state lives here;
    nothing about hashing does.
    """

    def __init__(
        self,
        callback: OptionalCallback,
        interval_ms: int,
        *,
        clock: Clock = time.monotonic,
    ) -> None:
        self._callback = callback
        self._consumed = 0
        self._interval = interval_ms / 1000.0  # seconds
        self._clock = clock
        self._reported = -1
        self._at = 0.0

    def _fire(self) -> None:
        """Report the running total, if there is a callback, and record it."""
        if self._callback is not None:
            self._callback(self._consumed)
        self._reported = self._consumed
        self._at = self._clock()

    def start(self) -> None:
        """Report 0 before the first chunk."""
        if self._reported != -1:
            raise RuntimeError("start called on already started reporter")
        self._fire()

    def advance(self, n: int) -> None:
        """Count n more bytes consumed; never reports."""
        self._consumed += n

    def maybe_report(self) -> None:
        """Report the running total if the interval has elapsed."""
        if self._clock() - self._at >= self._interval:
            self._fire()

    def finish(self) -> None:
        """Report the total unless it was the last value reported."""
        if self._reported != self._consumed:
            self._fire()


def digest_from_chunks(
    chunks: Iterable[bytes],
    bits: int,
    *,
    on_progress: OptionalCallback = None,
    interval_ms: int = 1000,
) -> bytes:
    """Digest an iterable of byte chunks at a certified width.

    Consumes chunks as the producer yields them; chunk size is the
    producer's concern. on_progress, if given, receives cumulative
    bytes consumed: once with 0 before the first chunk, then at most
    every progress_interval_ms (a minimum spacing, not exact), and once
    unconditionally after the last chunk with the true total, so the
    last value seen is always the total, 0 for empty input. Exceptions
    from the iterable or the callback propagate unchanged and no
    digest is ever returned for a partial feed.
    """
    reporter = _ProgressReporter(on_progress, interval_ms)
    reporter.start()
    hasher = _IncrementalDigest()
    for chunk in chunks:
        hasher.update(chunk)
        reporter.advance(len(chunk))
        reporter.maybe_report()
    reporter.finish()
    return hasher.digest(bits)
