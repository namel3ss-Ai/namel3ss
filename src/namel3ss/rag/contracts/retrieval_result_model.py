from __future__ import annotations

from namel3ss.rag.contracts.value_norms import int_value, map_value, merge_extensions, text_value, unknown_extensions
from namel3ss.rag.determinism.order_policy import normalize_score


RETRIEVAL_RESULT_SCHEMA_VERSION = "rag.retrieval_result@1"


def build_retrieval_result_model(
    *,
    rank: int,
    chunk_id: str,
    doc_id: str,
    page_number: int,
    score: object = 0,
    rerank_score: object = 0,
    score_bundle: object = None,
    reason_codes: object = None,
    schema_version: str = RETRIEVAL_RESULT_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    bundle = _normalize_score_bundle(score_bundle, score=score, rerank_score=rerank_score)
    return {
        "schema_version": text_value(schema_version, default=RETRIEVAL_RESULT_SCHEMA_VERSION) or RETRIEVAL_RESULT_SCHEMA_VERSION,
        "rank": int_value(rank, minimum=1, default=1),
        "chunk_id": text_value(chunk_id),
        "doc_id": text_value(doc_id),
        "page_number": int_value(page_number, minimum=1, default=1),
        "score": float(bundle["score"]),
        "rerank_score": float(bundle["rerank_score"]),
        "score_bundle": bundle,
        "reason_codes": _reason_codes(reason_codes),
        "extensions": merge_extensions(extensions),
    }


def normalize_retrieval_result_model(value: object) -> dict[str, object]:
    data = map_value(value)
    provided_extensions = map_value(data.get("extensions"))
    bundle = _normalize_score_bundle(
        data.get("score_bundle"),
        score=data.get("score"),
        rerank_score=data.get("rerank_score"),
    )
    extensions = merge_extensions(
        provided_extensions,
        unknown_extensions(data, known_keys=_KNOWN_FIELDS),
    )
    return {
        "schema_version": text_value(data.get("schema_version"), default=RETRIEVAL_RESULT_SCHEMA_VERSION) or RETRIEVAL_RESULT_SCHEMA_VERSION,
        "rank": int_value(data.get("rank"), minimum=1, default=1),
        "chunk_id": text_value(data.get("chunk_id")),
        "doc_id": text_value(data.get("doc_id")),
        "page_number": int_value(data.get("page_number"), minimum=1, default=1),
        "score": float(bundle["score"]),
        "rerank_score": float(bundle["rerank_score"]),
        "score_bundle": bundle,
        "reason_codes": _reason_codes(data.get("reason_codes")),
        "extensions": extensions,
    }


def _normalize_score_bundle(value: object, *, score: object, rerank_score: object) -> dict[str, float]:
    data = map_value(value)
    retrieval_score = normalize_score(data.get("score", score))
    rerank = normalize_score(data.get("rerank_score", rerank_score))
    keyword = normalize_score(data.get("keyword_score", 0))
    vector = normalize_score(data.get("vector_score", 0))
    return {
        "keyword_score": float(keyword),
        "rerank_score": float(rerank),
        "score": float(retrieval_score),
        "vector_score": float(vector),
    }


def _reason_codes(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    rows: list[str] = []
    for item in value:
        code = text_value(item)
        if not code or code in seen:
            continue
        seen.add(code)
        rows.append(code)
    return rows


_KNOWN_FIELDS = {
    "schema_version",
    "rank",
    "chunk_id",
    "doc_id",
    "page_number",
    "score",
    "rerank_score",
    "score_bundle",
    "reason_codes",
    "extensions",
}


__all__ = [
    "RETRIEVAL_RESULT_SCHEMA_VERSION",
    "build_retrieval_result_model",
    "normalize_retrieval_result_model",
]
