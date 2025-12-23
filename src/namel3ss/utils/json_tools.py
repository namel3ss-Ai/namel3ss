from __future__ import annotations

import json
from decimal import Decimal

from namel3ss.utils.numbers import decimal_is_int, decimal_to_str


def _json_default(value: object):
    if isinstance(value, Decimal):
        if decimal_is_int(value):
            return int(value)
        return decimal_to_str(value)
    raise TypeError(f"Object of type {type(value)} is not JSON serializable")


def dumps(obj: object, *, indent: int | None = None, sort_keys: bool = False) -> str:
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=sort_keys, default=_json_default)


def dumps_pretty(obj: object) -> str:
    return dumps(obj, indent=2, sort_keys=False)
