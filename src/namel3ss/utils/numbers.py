from __future__ import annotations

from decimal import Decimal


def is_number(value: object) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise TypeError("Boolean is not a numeric value")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    raise TypeError(f"Unsupported numeric type: {type(value)}")


def decimal_is_int(value: Decimal) -> bool:
    return value == value.to_integral_value()


def decimal_to_str(value: Decimal) -> str:
    return format(value.normalize(), "f")
