from __future__ import annotations

import json

from namel3ss.errors.base import Namel3ssError


def ensure_text_output(provider_name: str, text: object) -> str:
    if isinstance(text, str) and text.strip() != "":
        return text
    raise Namel3ssError(f"Provider '{provider_name}' returned an invalid response")


def json_loads_or_error(provider_name: str, raw: bytes) -> dict:
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as err:  # json.JSONDecodeError or UnicodeError
        raise Namel3ssError(f"Provider '{provider_name}' returned an invalid response") from err
