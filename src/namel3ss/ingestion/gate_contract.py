from __future__ import annotations

import hashlib
import json

PROBE_MAX_BYTES = 10_000_000
PROBE_SAMPLE_BYTES = 4096
PROBE_BINARY_RATIO_LIMIT = 300
EVIDENCE_EXCERPT_LIMIT = 160

REASON_EMPTY_CONTENT = "empty_content"
REASON_NULL_BYTES = "null_bytes"
REASON_SIZE_LIMIT = "size_limit"
REASON_UTF8_INVALID = "utf8_invalid"
REASON_BINARY_MARKERS = "binary_markers"
REASON_PDF_MISSING_EOF = "pdf_missing_eof"

PROBE_REASON_ORDER = (
    REASON_EMPTY_CONTENT,
    REASON_NULL_BYTES,
    REASON_SIZE_LIMIT,
    REASON_UTF8_INVALID,
    REASON_BINARY_MARKERS,
    REASON_PDF_MISSING_EOF,
)

QUALITY_REASON_ORDER = (
    "text_too_short",
    "low_unique_tokens",
    "high_non_ascii",
    "repeated_lines",
    "table_heavy",
    "many_empty_pages",
    "unreadable_text_pattern",
    "empty_text",
)

QUALITY_THRESHOLDS = {
    "text_chars_warn": 20,
    "text_chars_block": 50,
    "unique_token_ratio_warn": 0.2,
    "unique_token_ratio_block": 0.1,
    "non_ascii_ratio_warn": 0.5,
    "non_ascii_ratio_block": 0.8,
    "repeated_line_ratio_warn": 0.5,
    "repeated_line_ratio_block": 0.7,
    "table_like_ratio_warn": 0.6,
    "empty_pages_ratio_warn": 0.5,
    "uppercase_alpha_ratio_block": 0.9,
    "vowel_alpha_ratio_block": 0.22,
    "unreadable_text_chars_min": 80,
}



def gate_signature_payload() -> dict:
    return {
        "contract": "ingestion_gate",
        "probe": {
            "max_bytes": PROBE_MAX_BYTES,
            "sample_bytes": PROBE_SAMPLE_BYTES,
            "binary_ratio_limit": PROBE_BINARY_RATIO_LIMIT,
            "reasons": list(PROBE_REASON_ORDER),
        },
        "normalize": {
            "basis": "raw_bytes",
            "newline": "lf",
            "encoding": "utf-8",
            "excerpt_limit": EVIDENCE_EXCERPT_LIMIT,
        },
        "quality": {
            "reasons": list(QUALITY_REASON_ORDER),
            "thresholds": dict(QUALITY_THRESHOLDS),
        },
        "cache": {"key": "content_hash+runtime_signature"},
    }



def gate_runtime_signature() -> str:
    payload = gate_signature_payload()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "EVIDENCE_EXCERPT_LIMIT",
    "PROBE_BINARY_RATIO_LIMIT",
    "PROBE_MAX_BYTES",
    "PROBE_REASON_ORDER",
    "PROBE_SAMPLE_BYTES",
    "QUALITY_REASON_ORDER",
    "QUALITY_THRESHOLDS",
    "REASON_BINARY_MARKERS",
    "REASON_EMPTY_CONTENT",
    "REASON_NULL_BYTES",
    "REASON_PDF_MISSING_EOF",
    "REASON_SIZE_LIMIT",
    "REASON_UTF8_INVALID",
    "gate_runtime_signature",
    "gate_signature_payload",
]
