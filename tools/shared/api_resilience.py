from __future__ import annotations

import time
from dataclasses import dataclass


class TransientAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int
    base_delay: float
    max_delay: float


def call_with_retries(action, policy: RetryPolicy):
    attempt = 0
    while True:
        attempt += 1
        try:
            return action()
        except TransientAPIError:
            if attempt >= policy.max_attempts:
                raise
            delay = min(policy.max_delay, policy.base_delay * (2 ** (attempt - 1)))
            if delay > 0:
                time.sleep(delay)
