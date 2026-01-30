from __future__ import annotations

from namel3ss.ingestion.gate_contract import (
    PROBE_BINARY_RATIO_LIMIT,
    PROBE_MAX_BYTES,
    PROBE_REASON_ORDER,
    PROBE_SAMPLE_BYTES,
    REASON_BINARY_MARKERS,
    REASON_EMPTY_CONTENT,
    REASON_NULL_BYTES,
    REASON_PDF_MISSING_EOF,
    REASON_SIZE_LIMIT,
    REASON_UTF8_INVALID,
)


def probe_content(content: bytes | None, *, metadata: dict, detected: dict) -> dict:
    payload = content or b""
    byte_count = len(payload)
    null_bytes = payload.count(b"\x00")
    utf8_valid = _is_utf8(payload)
    sample = payload[: min(byte_count, PROBE_SAMPLE_BYTES)]
    binary_ratio = _binary_ratio(sample)
    sniff = "binary" if binary_ratio > PROBE_BINARY_RATIO_LIMIT else "text"

    detected_type = _text_value(detected.get("type"))
    content_type = _text_value(metadata.get("content_type"))
    pdf_eof = None
    if detected_type == "pdf":
        pdf_eof = _pdf_has_eof(payload)

    block_reasons: list[str] = []
    warn_reasons: list[str] = []
    if byte_count == 0:
        block_reasons.append(REASON_EMPTY_CONTENT)
    if null_bytes:
        block_reasons.append(REASON_NULL_BYTES)
    if byte_count > PROBE_MAX_BYTES:
        block_reasons.append(REASON_SIZE_LIMIT)
    if not utf8_valid:
        warn_reasons.append(REASON_UTF8_INVALID)
    if sniff == "binary" and detected_type == "text":
        warn_reasons.append(REASON_BINARY_MARKERS)
    if detected_type == "pdf" and pdf_eof is False:
        warn_reasons.append(REASON_PDF_MISSING_EOF)

    status = "block" if block_reasons else "pass"
    ordered_block = _ordered(block_reasons)
    ordered_warn = _ordered(warn_reasons)

    return {
        "status": status,
        "block_reasons": ordered_block,
        "warn_reasons": ordered_warn,
        "bytes": byte_count,
        "null_bytes": null_bytes,
        "utf8_valid": bool(utf8_valid),
        "binary_ratio": binary_ratio,
        "sniff": sniff,
        "sample_bytes": len(sample),
        "content_type": content_type,
        "detected_type": detected_type,
        "pdf_eof": pdf_eof,
    }


def _is_utf8(payload: bytes) -> bool:
    if not payload:
        return True
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _binary_ratio(sample: bytes) -> int:
    if not sample:
        return 0
    control = 0
    for value in sample:
        if value == 0:
            control += 1
            continue
        if value < 9:
            control += 1
            continue
        if 14 <= value < 32:
            control += 1
            continue
        if value == 127:
            control += 1
    return int(control * 1000 / max(len(sample), 1))


def _pdf_has_eof(payload: bytes) -> bool:
    if not payload:
        return False
    tail = payload[-2048:]
    return b"%%EOF" in tail


def _text_value(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _ordered(reasons: list[str]) -> list[str]:
    order = {reason: idx for idx, reason in enumerate(PROBE_REASON_ORDER)}
    return sorted({reason for reason in reasons if reason}, key=lambda item: order.get(item, 999))


__all__ = ["probe_content"]
