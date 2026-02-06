from __future__ import annotations

from namel3ss.determinism import canonical_json_dumps


def build_sse_body(yield_messages: list[dict], response: dict) -> bytes:
    lines: list[str] = []
    for message in yield_messages:
        lines.append("event: yield")
        lines.append(f"data: {canonical_json_dumps(message, pretty=False, drop_run_keys=False)}")
        lines.append("")
    lines.append("event: return")
    lines.append(f"data: {canonical_json_dumps(response, pretty=False, drop_run_keys=False)}")
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def sorted_yield_messages(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    rows: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sequence = _safe_int(item.get("sequence"))
        flow_name = str(item.get("flow_name") or "")
        payload = {
            "flow_name": flow_name,
            "output": item.get("output"),
            "sequence": sequence,
        }
        rows.append(payload)
    rows.sort(
        key=lambda entry: (
            int(entry.get("sequence") or 0),
            str(entry.get("flow_name") or ""),
            canonical_json_dumps(entry.get("output"), pretty=False, drop_run_keys=False),
        )
    )
    return rows


def should_stream_response(query: dict[str, str], headers: dict[str, str], yield_messages: list[dict]) -> bool:
    if yield_messages:
        return True
    stream = str(query.get("stream") or "").strip().lower()
    if stream in {"1", "true", "yes", "on"}:
        return True
    accept = str(headers.get("Accept") or headers.get("accept") or "").lower()
    if "text/event-stream" in accept:
        return True
    header_stream = str(headers.get("X-N3-Stream") or headers.get("x-n3-stream") or "").strip().lower()
    return header_stream in {"1", "true", "yes", "on"}


def _safe_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except Exception:
        return 0
    if parsed < 0:
        return 0
    return parsed


__all__ = [
    "build_sse_body",
    "should_stream_response",
    "sorted_yield_messages",
]
