from __future__ import annotations

import hashlib
import re


_WHITESPACE_RE = re.compile(r"\s+")


def canonical_chunk_text(value: str) -> str:
    text = value if isinstance(value, str) else ""
    return _WHITESPACE_RE.sub(" ", text.strip())


def stable_chunk_id(*, doc_id: str, page_number: int, chunk_index: int, text: str) -> str:
    canonical = canonical_chunk_text(text)
    payload = f"{doc_id.strip()}|{int(page_number)}|{int(chunk_index)}|{canonical}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{doc_id.strip()}:{int(page_number)}:{int(chunk_index)}:{digest[:20]}"


def stable_source_id(*, doc_id: str, page_number: int, chunk_index: int) -> str:
    return f"{doc_id.strip()}:{int(page_number)}:{int(chunk_index)}"


__all__ = ["canonical_chunk_text", "stable_chunk_id", "stable_source_id"]
