from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from namel3ss.observability.scrub import scrub_payload
from namel3ss.secrets import collect_secret_values

from namel3ss.runtime.composition.explain.bounds import API_VERSION
from namel3ss.runtime.composition.explain.call_tree import _build_call_tree
from namel3ss.runtime.composition.explain.orchestration import _build_orchestration_summary
from namel3ss.runtime.composition.explain.pipelines import _build_pipeline_summary


def build_composition_explain_pack(
    run_payload: dict | None,
    *,
    project_root: str | Path | None = None,
    app_path: str | Path | None = None,
    secret_values: Iterable[str] | None = None,
) -> dict:
    if not isinstance(run_payload, dict):
        return _scrub(_empty_pack("no_run"), project_root, app_path, secret_values)
    traces = _coerce_traces(run_payload)
    flow_name = _flow_name(run_payload)
    pack = {
        "ok": bool(run_payload.get("ok", True)),
        "api_version": API_VERSION,
        "flow_name": flow_name,
        "call_tree": _build_call_tree(traces, flow_name),
        "pipelines": _build_pipeline_summary(traces),
        "orchestration": _build_orchestration_summary(traces),
    }
    return _scrub(pack, project_root, app_path, secret_values)


def build_composition_explain_bundle(
    root: Path,
    *,
    app_path: str | Path | None = None,
    secret_values: Iterable[str] | None = None,
) -> dict:
    run_last = _load_last_run(root)
    return build_composition_explain_pack(
        run_last,
        project_root=root,
        app_path=app_path,
        secret_values=secret_values,
    )


def _empty_pack(reason: str) -> dict:
    return {
        "ok": False,
        "api_version": API_VERSION,
        "flow_name": "unknown",
        "reason": reason,
        "call_tree": {
            "root": {"id": "flow:unknown", "kind": "flow", "name": "unknown"},
            "calls": [],
            "total": 0,
            "truncated": False,
        },
        "pipelines": {
            "runs": [],
            "total_runs": 0,
            "total_steps": 0,
            "runs_truncated": False,
            "steps_truncated": False,
        },
        "orchestration": {
            "runs": [],
            "total_runs": 0,
            "runs_truncated": False,
        },
    }


def _coerce_traces(run_payload: dict) -> list[dict]:
    traces = run_payload.get("traces")
    if not isinstance(traces, list):
        contract = run_payload.get("contract") if isinstance(run_payload.get("contract"), dict) else {}
        traces = contract.get("traces") if isinstance(contract.get("traces"), list) else []
    return [trace for trace in traces if isinstance(trace, dict)]


def _flow_name(run_payload: dict) -> str:
    name = run_payload.get("flow_name")
    if isinstance(name, str) and name:
        return name
    contract = run_payload.get("contract") if isinstance(run_payload.get("contract"), dict) else {}
    name = contract.get("flow_name")
    if isinstance(name, str) and name:
        return name
    return "unknown"


def _scrub(
    payload: dict,
    project_root: str | Path | None,
    app_path: str | Path | None,
    secret_values: Iterable[str] | None,
) -> dict:
    secrets = list(secret_values) if secret_values is not None else collect_secret_values()
    scrubbed = scrub_payload(payload, secret_values=secrets, project_root=project_root, app_path=app_path)
    return scrubbed if isinstance(scrubbed, dict) else payload


def _load_last_run(root: Path) -> dict | None:
    path = root / ".namel3ss" / "run" / "last.json"
    return _load_json(path)


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


__all__ = ["build_composition_explain_pack", "build_composition_explain_bundle"]
