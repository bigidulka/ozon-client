"""Throttle: token bucket with jitter, sized for one fixed IP.

Measured on 2026-10-15 against ozon.by (short ladder, not a budget):

  - 40 concurrent requests   -> all 200, 402 ms wall
  - sustained sequential     -> 21 req / 5.2 s  (~4 rps), all 200
  - no 429 / Retry-After observed at any point of the ladder

That result is not a license to burst. On one IP, concurrency and a
metronome are louder than a polite 2 rps. Defaults are low-and-slow and
serialized: about one request every two seconds, burst 1, plus a random
pause so the gap is not constant. ``rate=0`` disables the bucket (cookie
minting and one-shot probes). ``burst > 1`` is the opt-in for a short
burst; in-flight overlap still requires the caller to actually run
concurrently. Pass ``jitter=0`` only in tests.
"""
import random
import threading
import time


class TokenBucket:
    """Thread-safe token bucket. ``rate=0`` disables throttling and jitter."""

    def __init__(self, rate: float = 0.5, burst: float = 1.0,
                 jitter: float | tuple[float, float] = (0.35, 1.15)):
        self.rate = float(rate)
        # capacity must be able to hold one full request, otherwise acquire()
        # could wait for tokens that can never accumulate -> hang forever.
        self.burst = max(float(burst), 1.0)
        if isinstance(jitter, tuple):
            self.jitter_min = float(jitter[0])
            self.jitter_max = float(jitter[1])
        else:
            self.jitter_min = 0.0
            self.jitter_max = float(jitter)
        if self.jitter_max < self.jitter_min:
            self.jitter_min, self.jitter_max = self.jitter_max, self.jitter_min
        self._tokens = self.burst
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> float:
        """Block until ``tokens`` are available, then sleep a random extra.

        Returns seconds slept (token wait + jitter). A request larger than
        the bucket capacity is served immediately — it can never be
        satisfied. Jitter is skipped when the bucket is disabled so a CDP
        cookie read does not pause.
        """
        if self.rate <= 0:
            return 0.0
        if tokens > self.burst:
            return 0.0
        slept = 0.0
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self.burst, self._tokens + (now - self._last) * self.rate
                )
                self._last = now
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    break
                wait = (tokens - self._tokens) / self.rate
            time.sleep(min(wait, 5.0))
            slept += min(wait, 5.0)
        extra = 0.0
        if self.jitter_max > 0:
            extra = random.uniform(self.jitter_min, self.jitter_max)
            if extra > 0:
                time.sleep(extra)
        return slept + extra
