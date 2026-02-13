from __future__ import annotations

from namel3ss.rag.contracts.value_norms import map_value, merge_extensions, text_value, unknown_extensions
from namel3ss.rag.determinism.id_policy import (
    build_content_hash,
    build_doc_id,
    build_doc_version_id,
)


DOCUMENT_SCHEMA_VERSION = "rag.document@1"


def build_document_model(
    *,
    source_type: str,
    source_identity: str,
    source_uri: str = "",
    title: str = "",
    mime_type: str = "",
    content: object = "",
    schema_version: str = DOCUMENT_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    source_type_value = text_value(source_type, default="upload") or "upload"
    source_identity_value = text_value(source_identity) or text_value(source_uri)
    content_hash = build_content_hash(content)
    doc_id = build_doc_id(source_type=source_type_value, source_identity=source_identity_value)
    doc_version_id = build_doc_version_id(content_hash=content_hash)
    return {
        "schema_version": text_value(schema_version, default=DOCUMENT_SCHEMA_VERSION) or DOCUMENT_SCHEMA_VERSION,
        "doc_id": doc_id,
        "doc_version_id": doc_version_id,
        "source_type": source_type_value,
        "source_identity": source_identity_value,
        "source_uri": text_value(source_uri),
        "content_hash": content_hash,
        "title": text_value(title),
        "mime_type": text_value(mime_type),
        "extensions": merge_extensions(extensions),
    }


def normalize_document_model(value: object) -> dict[str, object]:
    data = map_value(value)
    provided_extensions = map_value(data.get("extensions"))
    source_type = text_value(data.get("source_type"), default="upload") or "upload"
    source_uri = text_value(data.get("source_uri"))
    source_identity = text_value(data.get("source_identity")) or source_uri
    content_hash = text_value(data.get("content_hash"))
    if not content_hash:
        content_hash = build_content_hash(data.get("content", ""))
    doc_id = text_value(data.get("doc_id")) or build_doc_id(source_type=source_type, source_identity=source_identity)
    doc_version_id = text_value(data.get("doc_version_id")) or build_doc_version_id(content_hash=content_hash)
    extensions = merge_extensions(
        provided_extensions,
        unknown_extensions(data, known_keys=_KNOWN_FIELDS),
    )
    return {
        "schema_version": text_value(data.get("schema_version"), default=DOCUMENT_SCHEMA_VERSION) or DOCUMENT_SCHEMA_VERSION,
        "doc_id": doc_id,
        "doc_version_id": doc_version_id,
        "source_type": source_type,
        "source_identity": source_identity,
        "source_uri": source_uri,
        "content_hash": content_hash,
        "title": text_value(data.get("title")),
        "mime_type": text_value(data.get("mime_type")),
        "extensions": extensions,
    }


_KNOWN_FIELDS = {
    "schema_version",
    "doc_id",
    "doc_version_id",
    "source_type",
    "source_identity",
    "source_uri",
    "content_hash",
    "title",
    "mime_type",
    "extensions",
    "content",
}


__all__ = [
    "DOCUMENT_SCHEMA_VERSION",
    "build_document_model",
    "normalize_document_model",
]
