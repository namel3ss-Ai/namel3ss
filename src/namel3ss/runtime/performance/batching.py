from __future__ import annotations

from typing import Iterable, Iterator, TypeVar


T = TypeVar("T")


def batched(items: Iterable[T], batch_size: int) -> Iterator[list[T]]:
    size = int(batch_size)
    if size <= 0:
        raise ValueError("batch_size must be >= 1")
    chunk: list[T] = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


__all__ = ["batched"]
