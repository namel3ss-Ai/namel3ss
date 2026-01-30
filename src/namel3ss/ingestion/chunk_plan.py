from __future__ import annotations

import json

from namel3ss.determinism import canonical_json_dumps
from namel3ss.runtime.native import NativeStatus, native_chunk_plan

DEFAULT_MAX_CHARS = 800
DEFAULT_OVERLAP = 100
REASON_SEGMENT = 1
DEFAULT_SCORE = 0


def plan_chunks(text: str, *, max_chars: int = DEFAULT_MAX_CHARS, overlap: int = DEFAULT_OVERLAP) -> dict:
    max_chars = _coerce_non_negative(max_chars)
    overlap = _coerce_non_negative(overlap)
    native = _native_plan(text, max_chars=max_chars, overlap=overlap)
    if native is not None:
        return native
    return _plan_chunks_python(text or "", max_chars=max_chars, overlap=overlap)


def plan_to_payload(plan: dict) -> bytes:
    payload = canonical_json_dumps(plan, pretty=False)
    return payload.encode("utf-8")


def _plan_chunks_python(text: str, *, max_chars: int, overlap: int) -> dict:
    if not text:
        return {"chunks": [], "max_chars": max_chars, "overlap": _effective_overlap(max_chars, overlap)}
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[dict] = []
    index = 0
    for para_index, para in enumerate(paragraphs):
        for start, segment in _split_with_overlap(para, max_chars=max_chars, overlap=overlap):
            length = len(segment)
            chunks.append(
                {
                    "index": index,
                    "paragraph_index": para_index,
                    "start": start,
                    "length": length,
                    "chars": length,
                    "reason_code": REASON_SEGMENT,
                    "score": DEFAULT_SCORE,
                }
            )
            index += 1
    return {"chunks": chunks, "max_chars": max_chars, "overlap": _effective_overlap(max_chars, overlap)}


def _split_with_overlap(text: str, *, max_chars: int, overlap: int) -> list[tuple[int, str]]:
    if max_chars <= 0:
        return [(0, text)] if text else []
    overlap = _effective_overlap(max_chars, overlap)
    output: list[tuple[int, str]] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        raw_segment = text[start:end]
        leading = len(raw_segment) - len(raw_segment.lstrip())
        trailing = len(raw_segment) - len(raw_segment.rstrip())
        segment = raw_segment.strip()
        if segment:
            segment_start = start + leading
            output.append((segment_start, segment))
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return output


def _effective_overlap(max_chars: int, overlap: int) -> int:
    if max_chars <= 0:
        return 0
    if overlap >= max_chars:
        return max_chars // 4
    return overlap


def _coerce_non_negative(value: int) -> int:
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, int_value)


def _native_plan(text: str, *, max_chars: int, overlap: int) -> dict | None:
    if not text:
        return None
    payload = text.encode("utf-8")
    outcome = native_chunk_plan(payload, max_chars=max_chars, overlap=overlap)
    if outcome.status != NativeStatus.OK or outcome.payload is None:
        return None
    try:
        data = json.loads(outcome.payload.decode("utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


__all__ = [
    "DEFAULT_MAX_CHARS",
    "DEFAULT_OVERLAP",
    "REASON_SEGMENT",
    "plan_chunks",
    "plan_to_payload",
]
