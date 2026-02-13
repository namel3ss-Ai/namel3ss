from __future__ import annotations

from namel3ss.rag.contracts.value_norms import (
    int_value,
    map_value,
    merge_extensions,
    normalize_bbox,
    normalize_span,
    normalize_token_positions,
    text_value,
    unknown_extensions,
)
from namel3ss.rag.determinism.id_policy import build_citation_id
from namel3ss.rag.determinism.text_normalizer import normalize_anchor_text


CITATION_SCHEMA_VERSION = "rag.citation@1"


def build_citation_model(
    *,
    doc_id: str,
    page_number: int,
    chunk_id: str,
    answer_span: object = None,
    preview_target: object = None,
    mention_index: int = 0,
    citation_id: str | None = None,
    schema_version: str = CITATION_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    answer_span_value = normalize_span(answer_span)
    preview_target_value = _normalize_preview_target(preview_target, page_number=page_number)
    citation_id_value = text_value(citation_id) or build_citation_id(
        doc_id=text_value(doc_id),
        page_number=int_value(page_number, minimum=1, default=1),
        chunk_id=text_value(chunk_id),
        answer_span=answer_span_value,
    )
    return {
        "schema_version": text_value(schema_version, default=CITATION_SCHEMA_VERSION) or CITATION_SCHEMA_VERSION,
        "citation_id": citation_id_value,
        "doc_id": text_value(doc_id),
        "page_number": int_value(page_number, minimum=1, default=1),
        "chunk_id": text_value(chunk_id),
        "answer_span": answer_span_value,
        "preview_target": preview_target_value,
        "mention_index": int_value(mention_index, minimum=0, default=0),
        "extensions": merge_extensions(extensions),
    }


def normalize_citation_model(value: object) -> dict[str, object]:
    data = map_value(value)
    provided_extensions = map_value(data.get("extensions"))
    page_number = int_value(data.get("page_number"), minimum=1, default=1)
    answer_span = normalize_span(data.get("answer_span"))
    preview_target = _normalize_preview_target(data.get("preview_target"), page_number=page_number)
    citation_id_value = text_value(data.get("citation_id")) or build_citation_id(
        doc_id=text_value(data.get("doc_id")),
        page_number=page_number,
        chunk_id=text_value(data.get("chunk_id")),
        answer_span=answer_span,
    )
    extensions = merge_extensions(
        provided_extensions,
        unknown_extensions(data, known_keys=_KNOWN_FIELDS),
    )
    return {
        "schema_version": text_value(data.get("schema_version"), default=CITATION_SCHEMA_VERSION) or CITATION_SCHEMA_VERSION,
        "citation_id": citation_id_value,
        "doc_id": text_value(data.get("doc_id")),
        "page_number": page_number,
        "chunk_id": text_value(data.get("chunk_id")),
        "answer_span": answer_span,
        "preview_target": preview_target,
        "mention_index": int_value(data.get("mention_index"), minimum=0, default=0),
        "extensions": extensions,
    }


def _normalize_preview_target(value: object, *, page_number: int) -> dict[str, object]:
    data = map_value(value)
    target_page = int_value(data.get("page"), minimum=1, default=int_value(page_number, minimum=1, default=1))
    payload: dict[str, object] = {"page": target_page}
    bbox = normalize_bbox(data.get("bbox"))
    span = _optional_span(data.get("span"))
    token_positions = normalize_token_positions(data.get("token_positions"))
    anchor = normalize_anchor_text(data.get("anchor"))
    if bbox:
        payload["bbox"] = bbox
    if span is not None:
        payload["span"] = span
    if token_positions:
        payload["token_positions"] = token_positions
    if anchor:
        payload["anchor"] = anchor
    return payload


def _optional_span(value: object) -> dict[str, int] | None:
    span = normalize_span(value)
    start_char = int_value(span.get("start_char"), minimum=0, default=0)
    end_char = int_value(span.get("end_char"), minimum=start_char, default=start_char)
    if end_char <= start_char:
        return None
    return {
        "end_char": end_char,
        "start_char": start_char,
    }


_KNOWN_FIELDS = {
    "schema_version",
    "citation_id",
    "doc_id",
    "page_number",
    "chunk_id",
    "answer_span",
    "preview_target",
    "mention_index",
    "extensions",
}


__all__ = [
    "CITATION_SCHEMA_VERSION",
    "build_citation_model",
    "normalize_citation_model",
]
