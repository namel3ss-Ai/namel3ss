from __future__ import annotations

import json
from decimal import Decimal
from typing import Iterable

from namel3ss.determinism import canonical_json_dumps
from namel3ss.lexer.tokens import Token


def tokens_to_payload(tokens: Iterable[Token]) -> bytes:
    items = []
    for tok in tokens:
        items.append(
            {
                "type": tok.type,
                "value": _token_value(tok),
                "line": int(tok.line),
                "column": int(tok.column),
                "escaped": bool(tok.escaped),
            }
        )
    payload = canonical_json_dumps(items, pretty=False)
    return payload.encode("utf-8")


def payload_to_tokens(payload: bytes) -> list[Token]:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError("Invalid scan payload") from exc
    if not isinstance(raw, list):
        raise ValueError("Scan payload must be a list")
    tokens: list[Token] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Scan payload entries must be objects")
        token_type = item.get("type")
        if not isinstance(token_type, str) or not token_type:
            raise ValueError("Scan payload token type missing")
        line = item.get("line")
        column = item.get("column")
        if not isinstance(line, int) or not isinstance(column, int):
            raise ValueError("Scan payload line/column missing")
        escaped = bool(item.get("escaped", False))
        value = _parse_value(token_type, item.get("value"))
        tokens.append(Token(token_type, value, line, column, escaped=escaped))
    return tokens


def _token_value(tok: Token) -> str | None:
    value = tok.value
    if value is None:
        return None
    if tok.type == "NUMBER" and isinstance(value, Decimal):
        return format(value, "f")
    if tok.type == "BOOLEAN" and isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _parse_value(token_type: str, value: object) -> object | None:
    if value is None:
        return None
    if token_type == "NUMBER":
        return Decimal(str(value))
    if token_type == "BOOLEAN":
        text = str(value).strip().lower()
        return text == "true"
    return str(value)


__all__ = ["payload_to_tokens", "tokens_to_payload"]
