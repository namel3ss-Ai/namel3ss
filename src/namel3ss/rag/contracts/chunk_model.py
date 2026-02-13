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
from namel3ss.rag.determinism.id_policy import build_chunk_id
from namel3ss.rag.determinism.text_normalizer import (
    build_boundary_signature,
    canonical_text,
    normalize_anchor_text,
)


CHUNK_SCHEMA_VERSION = "rag.chunk@1"


def build_chunk_model(
    *,
    doc_id: str,
    page_number: int,
    chunk_index: int,
    text: object,
    span: object = None,
    bbox: object = None,
    token_positions: object = None,
    anchor: object = "",
    schema_version: str = CHUNK_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    doc_id_value = text_value(doc_id)
    page_number_value = int_value(page_number, minimum=1, default=1)
    chunk_index_value = int_value(chunk_index, minimum=0, default=0)
    text_value_normalized = canonical_text(text)
    boundary_signature = build_boundary_signature(
        doc_id=doc_id_value,
        page_number=page_number_value,
        chunk_index=chunk_index_value,
        text=text_value_normalized,
    )
    chunk_id = build_chunk_id(
        doc_id=doc_id_value,
        page_number=page_number_value,
        chunk_index=chunk_index_value,
        boundary_signature=boundary_signature,
    )
    anchor_text = normalize_anchor_text(anchor or text_value_normalized)
    return {
        "schema_version": text_value(schema_version, default=CHUNK_SCHEMA_VERSION) or CHUNK_SCHEMA_VERSION,
        "chunk_id": chunk_id,
        "doc_id": doc_id_value,
        "page_number": page_number_value,
        "chunk_index": chunk_index_value,
        "text": text_value_normalized,
        "boundary_signature": boundary_signature,
        "span": normalize_span(span),
        "bbox": normalize_bbox(bbox),
        "token_positions": normalize_token_positions(token_positions),
        "anchor": anchor_text,
        "extensions": merge_extensions(extensions),
    }


def normalize_chunk_model(value: object) -> dict[str, object]:
    data = map_value(value)
    provided_extensions = map_value(data.get("extensions"))
    doc_id = text_value(data.get("doc_id"))
    page_number = int_value(data.get("page_number"), minimum=1, default=1)
    chunk_index = int_value(data.get("chunk_index"), minimum=0, default=0)
    text = canonical_text(data.get("text"))
    boundary_signature = text_value(data.get("boundary_signature")) or build_boundary_signature(
        doc_id=doc_id,
        page_number=page_number,
        chunk_index=chunk_index,
        text=text,
    )
    chunk_id = text_value(data.get("chunk_id")) or build_chunk_id(
        doc_id=doc_id,
        page_number=page_number,
        chunk_index=chunk_index,
        boundary_signature=boundary_signature,
    )
    anchor = normalize_anchor_text(data.get("anchor") or text)
    extensions = merge_extensions(
        provided_extensions,
        unknown_extensions(data, known_keys=_KNOWN_FIELDS),
    )
    return {
        "schema_version": text_value(data.get("schema_version"), default=CHUNK_SCHEMA_VERSION) or CHUNK_SCHEMA_VERSION,
        "chunk_id": chunk_id,
        "doc_id": doc_id,
        "page_number": page_number,
        "chunk_index": chunk_index,
        "text": text,
        "boundary_signature": boundary_signature,
        "span": normalize_span(data.get("span")),
        "bbox": normalize_bbox(data.get("bbox")),
        "token_positions": normalize_token_positions(data.get("token_positions")),
        "anchor": anchor,
        "extensions": extensions,
    }


_KNOWN_FIELDS = {
    "schema_version",
    "chunk_id",
    "doc_id",
    "page_number",
    "chunk_index",
    "text",
    "boundary_signature",
    "span",
    "bbox",
    "token_positions",
    "anchor",
    "extensions",
}


__all__ = [
    "CHUNK_SCHEMA_VERSION",
    "build_chunk_model",
    "normalize_chunk_model",
]
