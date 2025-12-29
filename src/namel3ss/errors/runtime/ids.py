from __future__ import annotations

from namel3ss.errors.runtime.model import RuntimeWhere


def build_error_id(boundary: str, kind: str, where: RuntimeWhere, template_key: str) -> str:
    flow = _normalize_part(where.flow_name, fallback="NONE")
    stmt_kind = _normalize_part(where.statement_kind, fallback="NONE")
    index = where.statement_index or 0
    return f"E-{_normalize_part(boundary, fallback='ENGINE')}-{_normalize_part(kind, fallback='ERROR')}-{flow}-{stmt_kind}-{index}"


def _normalize_part(value: str | None, *, fallback: str) -> str:
    if not value:
        return fallback
    cleaned = []
    for char in str(value):
        if "A" <= char <= "Z" or "a" <= char <= "z" or "0" <= char <= "9":
            cleaned.append(char.upper())
        else:
            cleaned.append("_")
    normalized = "".join(cleaned).strip("_")
    return normalized or fallback


__all__ = ["build_error_id"]
