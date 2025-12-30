from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 0.2
    max_delay: float = 1.0


class TransientAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def call_with_retries(func: Callable[[], T], policy: RetryPolicy) -> T:
    attempt = 0
    last_error: TransientAPIError | None = None
    while attempt < policy.max_attempts:
        attempt += 1
        try:
            return func()
        except TransientAPIError as err:
            last_error = err
            if attempt >= policy.max_attempts:
                raise
            delay = min(policy.base_delay * (2 ** (attempt - 1)), policy.max_delay)
            time.sleep(delay)
    if last_error:
        raise last_error
    raise TransientAPIError("Retry attempts exhausted")


__all__ = ["RetryPolicy", "TransientAPIError", "call_with_retries"]
