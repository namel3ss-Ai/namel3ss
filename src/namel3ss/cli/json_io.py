from __future__ import annotations

import json

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.json_tools import dumps_pretty as json_dumps_pretty


def parse_payload(text: str | None) -> dict:
    if text is None or text == "":
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise Namel3ssError(_invalid_json_message(exc)) from exc
    if not isinstance(data, dict):
        raise Namel3ssError(_non_object_payload_message())
    return data


def dumps_pretty(obj: object) -> str:
    return json_dumps_pretty(obj)


def _invalid_json_message(exc: json.JSONDecodeError) -> str:
    where = f" at line {exc.lineno}, column {exc.colno}" if exc.lineno and exc.colno else ""
    return build_guidance_message(
        what="Invalid JSON payload.",
        why=f"JSON parsing failed{where}: {exc.msg}.",
        fix="Ensure the payload is valid JSON with double-quoted keys/strings.",
        example='{"values":{"name":"Ada"}}',
    )


def _non_object_payload_message() -> str:
    return build_guidance_message(
        what="Action payload must be a JSON object.",
        why="CLI payloads map to action inputs; lists, numbers, or strings cannot be unpacked.",
        fix='Wrap values in an object like {"values":{"email":"a@b.com"}} or pass "{}" for empty payloads.',
        example='n3 app.ai page.home.form.user "{\\"values\\":{\\"email\\":\\"ada@example.com\\"}}"',
    )
