from __future__ import annotations

from namel3ss.pipelines.model import PipelineStepResult
from namel3ss.traces.schema import TraceEventType


def answer_trace_from_steps(steps: list[PipelineStepResult]) -> dict | None:
    chunk_ids: list[str] = []
    prompt_hash: str | None = None
    citation_count = 0
    status = "unknown"
    for step in steps:
        summary = step.summary if isinstance(step.summary, dict) else {}
        if step.kind == "retrieve":
            value = summary.get("chunk_ids")
            if isinstance(value, list):
                chunk_ids = [str(item) for item in value]
        elif step.kind == "prompt":
            value = summary.get("prompt_hash")
            if isinstance(value, str) and value:
                prompt_hash = value
        elif step.kind == "validate":
            status_value = summary.get("status")
            if isinstance(status_value, str) and status_value:
                status = status_value
            count = summary.get("citation_count")
            if isinstance(count, (int, float)) and not isinstance(count, bool):
                citation_count = int(count)
    if not chunk_ids and prompt_hash is None and status == "unknown":
        return None
    return build_answer_trace(chunk_ids, prompt_hash, citation_count, status)


def answer_trace_from_error(error: Exception) -> dict | None:
    details = getattr(error, "details", None)
    if not isinstance(details, dict):
        return None
    trace = details.get("answer_trace")
    if not isinstance(trace, dict):
        return None
    chunk_ids = trace.get("chunk_ids")
    prompt_hash = trace.get("prompt_hash")
    citation_count = trace.get("citation_count")
    status = trace.get("status")
    return build_answer_trace(
        list(chunk_ids) if isinstance(chunk_ids, list) else [],
        str(prompt_hash) if isinstance(prompt_hash, str) else None,
        int(citation_count) if isinstance(citation_count, int) and not isinstance(citation_count, bool) else 0,
        str(status) if isinstance(status, str) and status else "error",
    )


def answer_explain_from_error(error: Exception) -> dict | None:
    details = getattr(error, "details", None)
    if not isinstance(details, dict):
        return None
    explain = details.get("answer_explain")
    if not isinstance(explain, dict):
        return None
    return build_answer_explain_trace(explain)


def build_answer_trace(
    chunk_ids: list[str],
    prompt_hash: str | None,
    citation_count: int,
    status: str,
) -> dict:
    return {
        "type": TraceEventType.ANSWER_VALIDATION,
        "chunk_ids": list(chunk_ids),
        "prompt_hash": prompt_hash,
        "citation_count": citation_count,
        "status": status,
    }


def build_answer_explain_trace(explain: dict) -> dict:
    return {
        "type": TraceEventType.ANSWER_EXPLAIN,
        "explain": dict(explain),
    }


def extract_answer_explain(traces: list[dict] | None) -> dict | None:
    if not isinstance(traces, list):
        return None
    for trace in reversed(traces):
        if not isinstance(trace, dict):
            continue
        if trace.get("type") != TraceEventType.ANSWER_EXPLAIN:
            continue
        explain = trace.get("explain")
        if isinstance(explain, dict):
            return dict(explain)
    return None


__all__ = [
    "answer_explain_from_error",
    "answer_trace_from_error",
    "answer_trace_from_steps",
    "build_answer_explain_trace",
    "build_answer_trace",
    "extract_answer_explain",
]
