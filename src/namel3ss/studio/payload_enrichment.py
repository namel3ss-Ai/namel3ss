from __future__ import annotations

from pathlib import Path
from typing import Mapping

from namel3ss.module_loader import load_project
from namel3ss.runtime.audit.audit_bundle import list_audit_bundles, load_run_artifact
from namel3ss.studio.diagnostics import (
    build_diagnostics_panel_payload,
    collect_ai_context_diagnostics,
)
from namel3ss.studio.diagnostics.ai_context import collect_runtime_ai_context_diagnostics
from namel3ss.studio.diff.run_diff import build_run_diff
from namel3ss.studio.session import SessionState
from namel3ss.studio.share.repro_bundle import load_repro_bundle


def attach_studio_metadata(payload: dict, session: SessionState | None) -> dict:
    if not isinstance(payload, dict):
        return payload
    if session is None:
        return payload
    workspace = session.workspace
    studio_session = session.studio_session
    if workspace is not None:
        payload["workspace_id"] = workspace.workspace_id
    if studio_session is not None:
        payload["session_id"] = studio_session.session_id
        payload["run_history"] = list(studio_session.run_ids)
    if isinstance(session.last_run_diff, dict) and session.last_run_diff:
        payload["run_diff"] = session.last_run_diff
    if isinstance(session.last_repro_bundle, dict) and session.last_repro_bundle:
        payload["repro_bundle"] = session.last_repro_bundle
    return payload


def record_run_artifact(payload: Mapping[str, object], session: SessionState | None) -> None:
    if session is None:
        return
    run_artifact = payload.get("run_artifact")
    if isinstance(run_artifact, Mapping):
        session.record_run_artifact(run_artifact)


def build_diagnostics_payload(source: str, session: SessionState | None, app_path: str) -> dict:
    app_file = Path(app_path).resolve()
    workspace = session.workspace if session else None
    studio_session = session.studio_session if session else None
    run_history = list(studio_session.run_ids) if studio_session else []
    latest_artifact = session.last_run_artifact if session else None
    if not latest_artifact and workspace and run_history:
        latest_artifact = load_run_artifact(workspace.project_root, run_id=run_history[-1])
    if not latest_artifact and workspace:
        latest_artifact = load_run_artifact(workspace.project_root)
    latest_diff = session.last_run_diff if session and isinstance(session.last_run_diff, dict) else None
    if not latest_diff and workspace and len(run_history) > 1:
        left = load_run_artifact(workspace.project_root, run_id=run_history[-2])
        right = load_run_artifact(workspace.project_root, run_id=run_history[-1])
        latest_diff = build_run_diff(left or {}, right or {})
    runtime_errors = session.runtime_errors if session else []
    panel = build_diagnostics_panel_payload(
        manifest={},
        state_snapshot=session.state if session else {},
        runtime_errors=runtime_errors,
        run_artifact=latest_artifact or {},
    )
    static_ai_diagnostics = _static_ai_context_diagnostics(source, app_file)
    runtime_ai_diagnostics = []
    if isinstance(latest_artifact, Mapping):
        output = latest_artifact.get("output")
        traces = []
        if isinstance(output, Mapping):
            output_traces = output.get("traces")
            if isinstance(output_traces, list):
                traces = output_traces
        runtime_ai_diagnostics = collect_runtime_ai_context_diagnostics(traces)
    payload = {
        "ok": True,
        "schema_version": 2,
        "diagnostics": panel.get("entries", []),
        "summary": panel.get("summary", {}),
        "ai_context_diagnostics": static_ai_diagnostics,
        "runtime_ai_context_diagnostics": runtime_ai_diagnostics,
        "run_diff": latest_diff or {},
        "run_history": _run_history_payload(
            workspace.project_root if workspace else app_file.parent.as_posix(),
            run_ids=run_history,
        ),
        "repro_bundle": _latest_repro_bundle(workspace.project_root if workspace else app_file.parent.as_posix()),
    }
    return attach_studio_metadata(payload, session)


def _static_ai_context_diagnostics(source: str, app_file: Path) -> list[dict]:
    try:
        project = load_project(app_file, source_overrides={app_file: source})
    except Exception:
        return []
    diagnostics = collect_ai_context_diagnostics(project.program)
    if not isinstance(diagnostics, list):
        return []
    return [entry for entry in diagnostics if isinstance(entry, dict)]


def _run_history_payload(project_root: str, *, run_ids: list[str]) -> list[dict[str, object]]:
    bundles = list_audit_bundles(project_root, limit=None)
    bundle_map = {}
    for bundle in bundles:
        if not isinstance(bundle, Mapping):
            continue
        run_id = _text(bundle.get("run_id"))
        if not run_id:
            continue
        bundle_map[run_id] = {
            "run_id": run_id,
            "integrity_hash": _text(bundle.get("integrity_hash")),
            "run_artifact_path": _text(bundle.get("run_artifact_path")),
        }
    ordered: list[dict[str, object]] = []
    seen: set[str] = set()
    for run_id in run_ids:
        text_run_id = _text(run_id)
        if not text_run_id or text_run_id in seen:
            continue
        seen.add(text_run_id)
        ordered.append(bundle_map.get(text_run_id) or {"run_id": text_run_id})
    if ordered:
        return ordered
    fallback = sorted(bundle_map.values(), key=lambda item: str(item.get("run_id") or ""))
    return fallback


def _latest_repro_bundle(project_root: str) -> dict[str, object]:
    bundle = load_repro_bundle(project_root)
    if isinstance(bundle, dict):
        return bundle
    return {}


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


__all__ = [
    "attach_studio_metadata",
    "build_diagnostics_payload",
    "record_run_artifact",
]
