from __future__ import annotations

from decimal import Decimal

from namel3ss.utils.numbers import decimal_to_str

_DECIMAL_KEY = "__n3_decimal__"


def encode_state(value: object) -> object:
    if isinstance(value, Decimal):
        return {_DECIMAL_KEY: decimal_to_str(value)}
    if isinstance(value, list):
        return [encode_state(v) for v in value]
    if isinstance(value, dict):
        return {k: encode_state(v) for k, v in value.items()}
    return value


def decode_state(value: object) -> object:
    if isinstance(value, list):
        return [decode_state(v) for v in value]
    if isinstance(value, dict):
        if set(value.keys()) == {_DECIMAL_KEY} and isinstance(value[_DECIMAL_KEY], str):
            return Decimal(value[_DECIMAL_KEY])
        return {k: decode_state(v) for k, v in value.items()}
    return value
