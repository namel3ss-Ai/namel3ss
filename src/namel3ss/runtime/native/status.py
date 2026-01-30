from __future__ import annotations

from enum import IntEnum
from typing import Iterable


class NativeStatus(IntEnum):
    OK = 0
    NOT_IMPLEMENTED = 1
    INVALID_ARGUMENT = 2
    INVALID_STATE = 3
    ERROR = 4


_ERROR_CODES = {
    NativeStatus.INVALID_ARGUMENT: "internal_error",
    NativeStatus.INVALID_STATE: "internal_error",
    NativeStatus.ERROR: "internal_error",
}


def status_from_int(value: int) -> NativeStatus:
    try:
        return NativeStatus(int(value))
    except (ValueError, TypeError):
        return NativeStatus.ERROR


def status_to_code(status: NativeStatus) -> str | None:
    return _ERROR_CODES.get(status)


def is_fallback_status(status: NativeStatus) -> bool:
    return status in {NativeStatus.OK, NativeStatus.NOT_IMPLEMENTED}


def known_status_values() -> tuple[int, ...]:
    return tuple(int(item.value) for item in NativeStatus)


def coerce_status(value: int | NativeStatus) -> NativeStatus:
    if isinstance(value, NativeStatus):
        return value
    return status_from_int(int(value))


def _unique(values: Iterable[int]) -> bool:
    seen: set[int] = set()
    for item in values:
        if item in seen:
            return False
        seen.add(item)
    return True


def status_values_are_unique() -> bool:
    return _unique(known_status_values())


__all__ = [
    "NativeStatus",
    "coerce_status",
    "is_fallback_status",
    "known_status_values",
    "status_from_int",
    "status_to_code",
    "status_values_are_unique",
]
