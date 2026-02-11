from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from namel3ss.module_loader import load_project
from namel3ss.runtime.retrieval.tag_filtering import resolve_filter_tags


def build_context_inspector_payload(
    *,
    source: str,
    app_path: str,
    state_snapshot: Mapping[str, object] | None,
    run_artifact: Mapping[str, object] | None,
) -> dict[str, object]:
    prompts = _compiled_prompt_summaries(source=source, app_path=app_path)
    runtime_prompt = _runtime_prompt_preview(run_artifact)
    retrieval_settings = _retrieval_settings(state_snapshot)
    filter_tags = resolve_filter_tags(None, state=state_snapshot)
    return {
        "studio_only": True,
        "compiled_prompt_context": prompts,
        "runtime_prompt_preview": runtime_prompt,
        "retrieval_settings": retrieval_settings,
        "filter_tags": filter_tags,
    }


def _compiled_prompt_summaries(*, source: str, app_path: str) -> list[dict[str, str]]:
    app_file = Path(app_path).resolve()
    try:
        project = load_project(app_file, source_overrides={app_file: source})
    except Exception:
        return []
    program = getattr(project, "program", None)
    flows = getattr(program, "flows", ()) if program is not None else ()
    summaries: list[dict[str, str]] = []
    for flow in sorted(flows, key=lambda entry: str(getattr(entry, "name", ""))):
        prompt_preview = _flow_prompt_preview(flow)
        if not prompt_preview:
            continue
        summaries.append(
            {
                "flow": str(getattr(flow, "name", "") or ""),
                "prompt_preview": prompt_preview,
            }
        )
    return summaries


def _flow_prompt_preview(flow: object) -> str:
    body = getattr(flow, "body", ())
    if not isinstance(body, list):
        return ""
    for stmt in body:
        if stmt.__class__.__name__ != "AskAIStmt":
            continue
        expr = getattr(stmt, "input_expr", None)
        return _expr_preview(expr)
    return ""


def _expr_preview(expr: object) -> str:
    if expr is None:
        return ""
    if expr.__class__.__name__ == "Literal":
        value = getattr(expr, "value", "")
        if isinstance(value, str):
            return _truncate(value)
    text = str(expr)
    return _truncate(" ".join(text.split()))


def _runtime_prompt_preview(run_artifact: Mapping[str, object] | None) -> str:
    artifact = run_artifact if isinstance(run_artifact, Mapping) else {}
    output = artifact.get("output")
    if not isinstance(output, Mapping):
        return ""
    traces = output.get("traces")
    if not isinstance(traces, list):
        return ""
    latest = ""
    for trace in traces:
        if not isinstance(trace, Mapping):
            continue
        if trace.get("ai_name") is None and trace.get("ai_profile_name") is None:
            continue
        value = trace.get("input")
        if isinstance(value, str) and value.strip():
            latest = value.strip()
    return _truncate(latest)


def _retrieval_settings(state_snapshot: Mapping[str, object] | None) -> dict[str, object]:
    state = state_snapshot if isinstance(state_snapshot, Mapping) else {}
    retrieval = state.get("retrieval")
    if not isinstance(retrieval, Mapping):
        return {}
    tuning = retrieval.get("tuning")
    if not isinstance(tuning, Mapping):
        return {}
    ordered_keys = ("semantic_k", "lexical_k", "final_top_k", "semantic_weight")
    return {
        key: tuning.get(key)
        for key in ordered_keys
        if key in tuning
    }


def _truncate(value: str) -> str:
    if len(value) <= 280:
        return value
    return f"{value[:280].rstrip()}..."


__all__ = ["build_context_inspector_payload"]
