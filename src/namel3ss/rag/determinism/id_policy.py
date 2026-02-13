from __future__ import annotations

import hashlib

from namel3ss.rag.determinism.json_policy import canonical_contract_hash
from namel3ss.rag.determinism.text_normalizer import canonical_text


def build_content_hash(content: object) -> str:
    text = canonical_text(content)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"content_{digest[:20]}"


def build_doc_id(*, source_type: str, source_identity: str) -> str:
    payload = {
        "source_identity": str(source_identity or "").strip(),
        "source_type": str(source_type or "").strip(),
    }
    return _stable_prefixed_id("doc", payload)


def build_doc_version_id(*, content_hash: str) -> str:
    payload = {"content_hash": str(content_hash or "").strip()}
    return _stable_prefixed_id("docv", payload)


def build_chunk_id(*, doc_id: str, page_number: int, chunk_index: int, boundary_signature: str) -> str:
    payload = {
        "boundary_signature": str(boundary_signature or "").strip(),
        "chunk_index": int(chunk_index),
        "doc_id": str(doc_id or "").strip(),
        "page_number": int(page_number),
    }
    return _stable_prefixed_id("chunk", payload)


def build_citation_id(
    *,
    doc_id: str,
    page_number: int,
    chunk_id: str,
    answer_span: dict[str, int] | None,
) -> str:
    span = answer_span if isinstance(answer_span, dict) else {}
    payload = {
        "chunk_id": str(chunk_id or "").strip(),
        "doc_id": str(doc_id or "").strip(),
        "page_number": int(page_number),
        "span_end": int(span.get("end_char") or 0),
        "span_start": int(span.get("start_char") or 0),
    }
    return _stable_prefixed_id("cit", payload)


def build_run_determinism_fingerprint(
    *,
    input_payload: dict[str, object],
    retrieval_config: dict[str, object],
    retrieved_chunk_ids: list[str],
) -> str:
    payload = {
        "input_payload": dict(input_payload),
        "retrieval_config": dict(retrieval_config),
        "retrieved_chunk_ids": [str(entry or "").strip() for entry in retrieved_chunk_ids],
    }
    return _stable_prefixed_id("runfp", payload)


def _stable_prefixed_id(prefix: str, payload: dict[str, object]) -> str:
    digest = canonical_contract_hash(payload)
    token = str(prefix or "").strip() or "id"
    return f"{token}_{digest[:20]}"


__all__ = [
    "build_citation_id",
    "build_chunk_id",
    "build_content_hash",
    "build_doc_id",
    "build_doc_version_id",
    "build_run_determinism_fingerprint",
]
