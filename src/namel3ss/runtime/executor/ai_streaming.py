from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone

from namel3ss.determinism import canonical_json_dumps
from namel3ss.runtime.explainability.logger import append_streaming_entry

_TOKEN_CHUNK_RE = re.compile(r"\S+\s*")
_LOGICAL_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def emit_ask_stream_events(
    ctx,
    stmt,
    output: object,
    *,
    provider_name: str,
    model_name: str,
) -> None:
    if not bool(getattr(stmt, "stream", False)):
        return
    if not streaming_enabled():
        return
    text = _coerce_output_text(output)
    chunks = _split_chunks(text)
    stream_id = _stream_id(ctx, stmt)
    _append_event(
        ctx,
        event_type="progress",
        output=None,
        stream_id=stream_id,
        data={
            "status": "started",
            "provider": provider_name,
            "model": model_name,
            "target": getattr(stmt, "target", ""),
            "chunk_count": len(chunks),
        },
    )
    for chunk in chunks:
        _append_event(
            ctx,
            event_type="token",
            output=chunk,
            stream_id=stream_id,
            data={
                "provider": provider_name,
                "model": model_name,
                "target": getattr(stmt, "target", ""),
            },
        )
    _append_event(
        ctx,
        event_type="finish",
        output=text,
        stream_id=stream_id,
        data={
            "status": "completed",
            "provider": provider_name,
            "model": model_name,
            "target": getattr(stmt, "target", ""),
            "chunk_count": len(chunks),
        },
    )


def streaming_enabled() -> bool:
    raw = str(os.getenv("NAMEL3SS_STREAMING_ENABLED", "true")).strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _split_chunks(text: str) -> list[str]:
    if not text:
        return []
    chunks = _TOKEN_CHUNK_RE.findall(text)
    if chunks:
        return chunks
    return [text]


def _coerce_output_text(output: object) -> str:
    if isinstance(output, str):
        return output
    if output is None:
        return ""
    return canonical_json_dumps(output, pretty=False, drop_run_keys=False)


def _stream_id(ctx, stmt) -> str:
    flow_name = str(getattr(getattr(ctx, "flow", None), "name", "") or "")
    ai_name = str(getattr(stmt, "ai_name", "") or "")
    start = int(getattr(ctx, "yield_sequence", 0)) + 1
    return f"{flow_name}:{ai_name}:{start}"


def _append_event(
    ctx,
    *,
    event_type: str,
    output: object,
    stream_id: str,
    data: dict[str, object],
) -> None:
    sequence = int(getattr(ctx, "yield_sequence", 0)) + 1
    ctx.yield_sequence = sequence
    timestamp = _logical_timestamp(sequence)
    ctx.yield_messages.append(
        {
            "flow_name": getattr(getattr(ctx, "flow", None), "name", ""),
            "output": output,
            "sequence": sequence,
            "event_type": event_type,
            "timestamp": timestamp,
            "data": data,
            "stream_id": stream_id,
            "stream_channel": "ai",
        }
    )
    append_streaming_entry(
        ctx,
        stream_id=stream_id,
        event_type=event_type,
        event_index=sequence,
        logical_time=timestamp,
        output=output,
        data=data,
    )


def _logical_timestamp(sequence: int) -> str:
    logical = _LOGICAL_EPOCH + timedelta(milliseconds=max(0, int(sequence)))
    return logical.isoformat(timespec="milliseconds").replace("+00:00", "Z")


__all__ = ["emit_ask_stream_events", "streaming_enabled"]
