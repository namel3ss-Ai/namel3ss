from __future__ import annotations

from namel3ss.rag.contracts.value_norms import normalize_bbox, normalize_span, normalize_token_positions
from namel3ss.rag.determinism.text_normalizer import canonical_text, normalize_anchor_text


HIGHLIGHT_MODE_BBOX = "bbox"
HIGHLIGHT_MODE_SPAN = "span"
HIGHLIGHT_MODE_TOKEN_POSITIONS = "token_positions"
HIGHLIGHT_MODE_ANCHOR = "anchor"
HIGHLIGHT_MODE_UNAVAILABLE = "unavailable"


def resolve_highlight_target(
    *,
    page_text: str,
    bbox: object = None,
    span: object = None,
    token_positions: object = None,
    anchor: object = None,
) -> dict[str, object]:
    text = str(page_text or "")
    span_value = _valid_span(span, text_length=len(text))
    token_span = _token_span(token_positions, text_length=len(text))
    anchor_span = _anchor_span(anchor, text)
    bbox_value = normalize_bbox(bbox)

    if bbox_value:
        payload = _exact_payload(HIGHLIGHT_MODE_BBOX, span_value or token_span or anchor_span)
        payload["bbox"] = bbox_value
        return payload
    if span_value is not None:
        return _exact_payload(HIGHLIGHT_MODE_SPAN, span_value)
    if token_span is not None:
        return _exact_payload(HIGHLIGHT_MODE_TOKEN_POSITIONS, token_span)
    if anchor_span is not None:
        return _exact_payload(HIGHLIGHT_MODE_ANCHOR, anchor_span)
    return _unavailable_payload()


def resolve_highlight_for_chunk(
    *,
    document_id: str,
    page_number: int,
    chunk_id: str,
    page_text: str,
    bbox: object = None,
    span: object = None,
    token_positions: object = None,
    anchor: object = None,
    citation_id: str | None = None,
) -> dict[str, object]:
    base = resolve_highlight_target(
        page_text=page_text,
        bbox=bbox,
        span=span,
        token_positions=token_positions,
        anchor=anchor,
    )
    payload: dict[str, object] = {
        "chunk_id": str(chunk_id or "").strip(),
        "document_id": str(document_id or "").strip(),
        "end_char": base.get("end_char"),
        "page_number": _positive(page_number, default=1),
        "resolver": str(base.get("resolver") or HIGHLIGHT_MODE_UNAVAILABLE),
        "start_char": base.get("start_char"),
        "status": str(base.get("status") or "unavailable"),
    }
    bbox_value = base.get("bbox")
    if isinstance(bbox_value, list) and bbox_value:
        payload["bbox"] = list(bbox_value)
    citation_text = str(citation_id or "").strip()
    if citation_text:
        payload["citation_id"] = citation_text
    return payload


def _exact_payload(mode: str, span: tuple[int, int] | None) -> dict[str, object]:
    start_char = None
    end_char = None
    if span is not None:
        start_char, end_char = span
    return {
        "end_char": end_char,
        "resolver": mode,
        "start_char": start_char,
        "status": "exact",
    }


def _unavailable_payload() -> dict[str, object]:
    return {
        "end_char": None,
        "resolver": HIGHLIGHT_MODE_UNAVAILABLE,
        "start_char": None,
        "status": "unavailable",
    }


def _valid_span(value: object, *, text_length: int) -> tuple[int, int] | None:
    span = normalize_span(value)
    start_char = _non_negative(span.get("start_char"), default=-1)
    end_char = _non_negative(span.get("end_char"), default=-1)
    if start_char < 0 or end_char <= start_char:
        return None
    if end_char > text_length:
        return None
    return (start_char, end_char)


def _token_span(value: object, *, text_length: int) -> tuple[int, int] | None:
    rows = normalize_token_positions(value)
    if not rows:
        return None
    spans: list[tuple[int, int]] = []
    for row in rows:
        span = _valid_span(
            {
                "start_char": row.get("start_char"),
                "end_char": row.get("end_char"),
            },
            text_length=text_length,
        )
        if span is None:
            continue
        spans.append(span)
    if not spans:
        return None
    starts = [item[0] for item in spans]
    ends = [item[1] for item in spans]
    return (min(starts), max(ends))


def _anchor_span(value: object, page_text: str) -> tuple[int, int] | None:
    if not page_text:
        return None
    anchor = normalize_anchor_text(value)
    if not anchor:
        return None
    lowered_page = page_text.lower()
    lowered_anchor = anchor.lower()
    index = lowered_page.find(lowered_anchor)
    if index < 0:
        normalized_page, offsets = _collapsed_text_with_offsets(page_text)
        normalized_anchor = canonical_text(anchor).lower()
        index = normalized_page.find(normalized_anchor)
        if index < 0:
            return None
        end_index = index + len(normalized_anchor)
        if end_index <= index or end_index > len(offsets):
            return None
        start_char = offsets[index]
        end_char = offsets[end_index - 1] + 1
        if end_char <= start_char:
            return None
        return (start_char, end_char)
    end_char = index + len(anchor)
    if end_char <= index:
        return None
    return (index, end_char)


def _collapsed_text_with_offsets(text: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    offsets: list[int] = []
    in_space = False
    for index, char in enumerate(text):
        if char.isspace():
            if in_space:
                continue
            chars.append(" ")
            offsets.append(index)
            in_space = True
            continue
        chars.append(char.lower())
        offsets.append(index)
        in_space = False
    raw = "".join(chars)
    if not raw.strip():
        return "", []
    left_trim = 0
    right_trim = len(raw)
    while left_trim < right_trim and raw[left_trim] == " ":
        left_trim += 1
    while right_trim > left_trim and raw[right_trim - 1] == " ":
        right_trim -= 1
    return raw[left_trim:right_trim], offsets[left_trim:right_trim]


def _non_negative(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value.is_integer() and int(value) >= 0:
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        if parsed >= 0:
            return parsed
    return default


def _positive(value: object, *, default: int) -> int:
    parsed = _non_negative(value, default=-1)
    if parsed > 0:
        return parsed
    return default


__all__ = [
    "HIGHLIGHT_MODE_ANCHOR",
    "HIGHLIGHT_MODE_BBOX",
    "HIGHLIGHT_MODE_SPAN",
    "HIGHLIGHT_MODE_TOKEN_POSITIONS",
    "HIGHLIGHT_MODE_UNAVAILABLE",
    "resolve_highlight_for_chunk",
    "resolve_highlight_target",
]
