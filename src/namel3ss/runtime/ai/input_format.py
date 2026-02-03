from __future__ import annotations

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.values.normalize import unwrap_text
from namel3ss.utils.numbers import is_number


TEXT_INPUT_MODE = "text"
STRUCTURED_INPUT_MODE = "structured"
STRUCTURED_INPUT_FORMAT = "structured_json_v1"


def prepare_ai_input(
    value: object,
    *,
    mode: str | None,
    line: int | None = None,
    column: int | None = None,
) -> tuple[str, object | None, str]:
    if mode == STRUCTURED_INPUT_MODE:
        _ensure_structured_value(value, line=line, column=column, path=())
        text = canonical_json_dumps(value, pretty=False, drop_run_keys=False)
        return text, value, STRUCTURED_INPUT_FORMAT
    if mode not in (None, TEXT_INPUT_MODE):
        raise Namel3ssError(f"Unknown AI input mode '{mode}'", line=line, column=column)
    text_value = unwrap_text(value)
    if not isinstance(text_value, str):
        raise Namel3ssError("AI input must be a string", line=line, column=column)
    return text_value, None, TEXT_INPUT_MODE


def _ensure_structured_value(
    value: object,
    *,
    line: int | None,
    column: int | None,
    path: tuple[object, ...],
) -> None:
    if value is None or isinstance(value, (str, bool)) or is_number(value):
        return
    if isinstance(value, dict):
        for key, child in value.items():
            _ensure_structured_key(key, line=line, column=column, path=path)
            _ensure_structured_value(child, line=line, column=column, path=path + (str(key),))
        return
    if isinstance(value, list):
        for idx, item in enumerate(value):
            _ensure_structured_value(item, line=line, column=column, path=path + (idx,))
        return
    if isinstance(value, tuple):
        for idx, item in enumerate(value):
            _ensure_structured_value(item, line=line, column=column, path=path + (idx,))
        return
    raise Namel3ssError(
        f"Structured AI input contains an unsupported value{_format_path(path)}.",
        line=line,
        column=column,
    )


def _ensure_structured_key(
    key: object,
    *,
    line: int | None,
    column: int | None,
    path: tuple[object, ...],
) -> None:
    if isinstance(key, (str, bool)) or is_number(key):
        return
    raise Namel3ssError(
        f"Structured AI input map keys must be text, number, or boolean{_format_path(path)}.",
        line=line,
        column=column,
    )


def _format_path(path: tuple[object, ...]) -> str:
    if not path:
        return ""
    parts: list[str] = []
    for item in path:
        if isinstance(item, int):
            parts.append(f"index {item}")
        else:
            parts.append(f"key '{item}'")
    return " at " + " -> ".join(parts)


__all__ = [
    "STRUCTURED_INPUT_FORMAT",
    "STRUCTURED_INPUT_MODE",
    "TEXT_INPUT_MODE",
    "prepare_ai_input",
]
