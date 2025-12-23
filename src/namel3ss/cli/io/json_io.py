from __future__ import annotations

import json

from namel3ss.errors.base import Namel3ssError
from namel3ss.utils.json_tools import dumps_pretty as json_dumps_pretty


def parse_json(text: str) -> dict:
    try:
        data = json.loads(text) if text else {}
    except json.JSONDecodeError as exc:
        raise Namel3ssError(f"Invalid JSON payload: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise Namel3ssError("Payload JSON must be an object")
    return data


def dumps_pretty(obj: object) -> str:
    return json_dumps_pretty(obj)
