from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def normalize_score(value: object, *, precision: int = 6) -> Decimal:
    if isinstance(value, bool):
        number = Decimal("0")
    else:
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            number = Decimal("0")
    places = max(0, int(precision))
    quant = Decimal("1") if places == 0 else Decimal("1").scaleb(-places)
    return number.quantize(quant, rounding=ROUND_HALF_UP)


def sort_retrieval_results(rows: list[dict]) -> list[dict]:
    normalized = [dict(entry) for entry in rows if isinstance(entry, dict)]
    normalized.sort(key=_retrieval_sort_key)
    return normalized


def sort_citation_rows(rows: list[dict]) -> list[dict]:
    normalized = [dict(entry) for entry in rows if isinstance(entry, dict)]
    normalized.sort(key=_citation_sort_key)
    return normalized


def _retrieval_sort_key(entry: dict) -> tuple[Decimal, Decimal, str, int, str]:
    score = normalize_score(_score_value(entry, "score", "retrieval_score"))
    rerank_score = normalize_score(_score_value(entry, "rerank_score", "score_rerank"))
    doc_id = _text(entry.get("doc_id") or entry.get("document_id"))
    page_number = _int(entry.get("page_number"))
    chunk_id = _text(entry.get("chunk_id"))
    return (-score, -rerank_score, doc_id, page_number, chunk_id)


def _citation_sort_key(entry: dict) -> tuple[int, str, int, str, str]:
    mention_index = _int(entry.get("mention_index"), default=0)
    doc_id = _text(entry.get("doc_id") or entry.get("document_id"))
    page_number = _int(entry.get("page_number"))
    chunk_id = _text(entry.get("chunk_id"))
    citation_id = _text(entry.get("citation_id"))
    return (mention_index, doc_id, page_number, chunk_id, citation_id)


def _score_value(entry: dict, primary_key: str, fallback_key: str) -> object:
    if primary_key in entry:
        return entry.get(primary_key)
    return entry.get(fallback_key)


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _int(value: object, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except Exception:
        return default


__all__ = [
    "normalize_score",
    "sort_citation_rows",
    "sort_retrieval_results",
]
