from __future__ import annotations

import hashlib
import re
import unicodedata


_WHITESPACE_RE = re.compile(r"\s+")


def canonical_text(value: object) -> str:
    text = value if isinstance(value, str) else ""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").strip()
    return _WHITESPACE_RE.sub(" ", normalized)


def normalize_anchor_text(value: object, *, max_chars: int = 160) -> str:
    text = canonical_text(value)
    if not text:
        return ""
    limit = max(0, int(max_chars))
    if limit <= 0:
        return ""
    return text[:limit]


def build_boundary_signature(*, doc_id: str, page_number: int, chunk_index: int, text: object) -> str:
    canonical = canonical_text(text)
    payload = f"{str(doc_id).strip()}|{int(page_number)}|{int(chunk_index)}|{canonical}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"bsig_{digest[:20]}"


__all__ = [
    "build_boundary_signature",
    "canonical_text",
    "normalize_anchor_text",
]
