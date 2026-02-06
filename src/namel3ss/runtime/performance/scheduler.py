from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class SchedulerStats:
    interactive_slots: int
    heavy_slots: int
    interactive_wait_ms: int
    heavy_wait_ms: int


class DeterministicTaskScheduler:
    def __init__(self, *, max_concurrency: int) -> None:
        total = max(1, int(max_concurrency))
        interactive_slots = max(1, total // 2)
        heavy_slots = max(1, total - interactive_slots)
        self._interactive = threading.BoundedSemaphore(interactive_slots)
        self._heavy = threading.BoundedSemaphore(heavy_slots)
        self._interactive_slots = interactive_slots
        self._heavy_slots = heavy_slots
        self._lock = threading.Lock()
        self._interactive_wait_ms = 0
        self._heavy_wait_ms = 0

    def run_interactive(self, fn: Callable[[], T]) -> tuple[T, int]:
        return self._run(self._interactive, kind="interactive", fn=fn)

    def run_heavy(self, fn: Callable[[], T]) -> tuple[T, int]:
        return self._run(self._heavy, kind="heavy", fn=fn)

    def stats(self) -> SchedulerStats:
        with self._lock:
            return SchedulerStats(
                interactive_slots=self._interactive_slots,
                heavy_slots=self._heavy_slots,
                interactive_wait_ms=self._interactive_wait_ms,
                heavy_wait_ms=self._heavy_wait_ms,
            )

    def _run(self, semaphore: threading.BoundedSemaphore, *, kind: str, fn: Callable[[], T]) -> tuple[T, int]:
        started = time.monotonic()
        semaphore.acquire()
        wait_ms = int((time.monotonic() - started) * 1000)
        try:
            self._record_wait(kind=kind, wait_ms=wait_ms)
            return fn(), wait_ms
        finally:
            semaphore.release()

    def _record_wait(self, *, kind: str, wait_ms: int) -> None:
        with self._lock:
            if kind == "interactive":
                self._interactive_wait_ms += int(wait_ms)
                return
            self._heavy_wait_ms += int(wait_ms)


__all__ = ["DeterministicTaskScheduler", "SchedulerStats"]
