from __future__ import annotations

from namel3ss.runtime.answer.api import build_answer_prompt, hash_answer_prompt


def build_chat_prompt(*, query: str, retrieval_rows: list[dict[str, object]]) -> dict[str, object]:
    ordered_rows = _ordered_rows(retrieval_rows)
    prompt = build_answer_prompt(_query_text(query), ordered_rows)
    return {
        "prompt": prompt,
        "prompt_hash": hash_answer_prompt(prompt),
        "source_count": len(ordered_rows),
    }


def _ordered_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized = [dict(row) for row in rows if isinstance(row, dict)]
    normalized.sort(
        key=lambda row: (
            _non_negative(row.get("rank"), default=0),
            _text(row.get("document_id")),
            _positive(row.get("page_number"), default=1),
            _non_negative(row.get("chunk_index"), default=0),
            _text(row.get("chunk_id")),
        )
    )
    return normalized


def _query_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _positive(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value.is_integer() and int(value) > 0:
        return int(value)
    return default


def _non_negative(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value.is_integer() and int(value) >= 0:
        return int(value)
    return default


__all__ = [
    "build_chat_prompt",
]
