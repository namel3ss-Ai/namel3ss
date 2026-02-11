from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from namel3ss.module_loader import load_project
from namel3ss.studio.panels.retrieval_trace_panel import build_retrieval_trace_panel_payload


def build_retrieval_trace_payload(
    *,
    source: str,
    app_path: str,
    run_artifact: Mapping[str, object] | None,
) -> dict[str, object]:
    project_caps, source_map = _project_trace_context(source=source, app_path=app_path)
    trace_payload = _extract_trace_payload(run_artifact)
    return build_retrieval_trace_panel_payload(
        trace_payload=trace_payload,
        capabilities=project_caps,
        source_map=source_map,
    )


def _project_trace_context(*, source: str, app_path: str) -> tuple[tuple[str, ...], list[dict[str, object]]]:
    app_file = Path(app_path).resolve()
    try:
        project = load_project(app_file, source_overrides={app_file: source})
    except Exception:
        return (), []
    program = getattr(project, "program", None)
    capabilities = tuple(getattr(program, "capabilities", ()) or ()) if program is not None else ()
    source_map_raw = getattr(program, "composition_source_map", None) if program is not None else None
    source_map = _normalize_source_map(source_map_raw)
    return capabilities, source_map


def _extract_trace_payload(run_artifact: Mapping[str, object] | None) -> dict[str, object] | None:
    artifact = run_artifact if isinstance(run_artifact, Mapping) else {}
    output = artifact.get("output")
    output_map = output if isinstance(output, Mapping) else {}
    retrieval = output_map.get("retrieval")
    retrieval_map = retrieval if isinstance(retrieval, Mapping) else {}
    trace = retrieval_map.get("retrieval_trace_diagnostics")
    if isinstance(trace, Mapping):
        return {str(key): trace[key] for key in trace.keys()}
    fallback = output_map.get("retrieval_trace_diagnostics")
    if isinstance(fallback, Mapping):
        return {str(key): fallback[key] for key in fallback.keys()}
    return None


def _normalize_source_map(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for entry in value:
        if not isinstance(entry, Mapping):
            continue
        rows.append({str(key): entry[key] for key in entry.keys()})
    return rows


__all__ = ["build_retrieval_trace_payload"]
