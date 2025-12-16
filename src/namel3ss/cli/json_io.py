from __future__ import annotations

import json

from namel3ss.errors.base import Namel3ssError


def parse_payload(text: str | None) -> dict:
    if text is None or text == "":
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise Namel3ssError(f"Invalid JSON payload: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise Namel3ssError("Payload must be a JSON object")
    return data


def dumps_pretty(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)
