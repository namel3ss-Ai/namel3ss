from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.request import Request, urlopen

from namel3ss.determinism import canonical_json_dump, canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.observability.config import load_observability_config
from namel3ss.observability.trace_runs import list_trace_runs, read_trace_entries, trace_runs_root


OTLP_RETRY_FILENAME = "otlp_retry.json"


def export_trace_runs(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    run_ids: list[str] | None = None,
) -> dict[str, object]:
    config = load_observability_config(project_root, app_path)
    endpoint = config.otlp_config.endpoint.strip()
    if not endpoint:
        raise Namel3ssError(_missing_endpoint_message())

    available = list_trace_runs(project_root, app_path)
    selected = _select_runs(available, run_ids)
    spans = _build_spans(project_root, app_path, selected)
    if not spans:
        return {"ok": True, "endpoint": endpoint, "runs": [], "exported_spans": 0, "failed_batches": 0}

    batch_size = config.otlp_config.batch_size
    batches = [spans[i : i + batch_size] for i in range(0, len(spans), batch_size)]
    failed_batches: list[dict[str, object]] = []
    exported_spans = 0
    for batch in batches:
        payload = {"resource": {"service.name": "namel3ss"}, "spans": batch}
        try:
            _post_json(endpoint=endpoint, payload=payload, auth=config.otlp_config.auth)
            exported_spans += len(batch)
        except Exception as err:
            failed_batches.append({"error": str(err), "payload": payload})
    if failed_batches:
        _append_retry_batches(project_root, app_path, endpoint=endpoint, items=failed_batches)
    return {
        "ok": not failed_batches,
        "endpoint": endpoint,
        "runs": [item["run_id"] for item in selected],
        "exported_spans": exported_spans,
        "failed_batches": len(failed_batches),
    }


def _select_runs(available: list[dict[str, object]], run_ids: list[str] | None) -> list[dict[str, object]]:
    if not run_ids:
        return sorted(available, key=lambda item: str(item.get("run_id", "")))
    wanted = {item.strip() for item in run_ids if item and item.strip()}
    selected = [item for item in available if str(item.get("run_id", "")) in wanted]
    selected.sort(key=lambda item: str(item.get("run_id", "")))
    return selected


def _build_spans(
    project_root: str | Path | None,
    app_path: str | Path | None,
    runs: list[dict[str, object]],
) -> list[dict[str, object]]:
    spans: list[dict[str, object]] = []
    for run in runs:
        run_id = str(run.get("run_id", "") or "")
        if not run_id:
            continue
        entries = read_trace_entries(project_root, app_path, run_id)
        for entry in entries:
            span = {
                "trace_id": run_id,
                "span_id": str(entry.get("step_id", "")),
                "name": str(entry.get("step_name", "")),
                "kind": "internal",
                "start_step": int(entry.get("timestamp", 0)),
                "end_step": int(entry.get("timestamp", 0)),
                "attributes": {
                    "flow_name": str(entry.get("flow_name", "")),
                    "duration_ms": float(entry.get("duration_ms", 0.0)),
                    "memory_used": int(entry.get("memory_used", 0)),
                },
            }
            spans.append(span)
    spans.sort(key=lambda item: (str(item.get("trace_id", "")), int(item.get("start_step", 0)), str(item.get("span_id", ""))))
    return spans


def _post_json(*, endpoint: str, payload: dict[str, object], auth: dict[str, object]) -> None:
    body = canonical_json_dumps(payload, pretty=False, drop_run_keys=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    auth_headers = _auth_headers(auth)
    headers.update(auth_headers)
    request = Request(endpoint, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=5) as response:  # nosec B310 - controlled via user config
        _ = response.read()


def _auth_headers(auth: dict[str, object]) -> dict[str, str]:
    if not auth:
        return {}
    token = auth.get("token")
    if isinstance(token, str) and token.strip():
        return {"Authorization": f"Bearer {token.strip()}"}
    username = auth.get("username")
    password = auth.get("password")
    if isinstance(username, str) and isinstance(password, str):
        raw = f"{username}:{password}".encode("utf-8")
        encoded = base64.b64encode(raw).decode("ascii")
        return {"Authorization": f"Basic {encoded}"}
    return {}


def _append_retry_batches(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    endpoint: str,
    items: list[dict[str, object]],
) -> None:
    root = trace_runs_root(project_root, app_path, allow_create=True)
    if root is None:
        return
    root.mkdir(parents=True, exist_ok=True)
    path = root / OTLP_RETRY_FILENAME
    payload = {"endpoint": endpoint, "batches": []}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        except Exception:
            payload = {"endpoint": endpoint, "batches": []}
    batches = payload.get("batches")
    if not isinstance(batches, list):
        batches = []
    batches.extend(items)
    payload["endpoint"] = endpoint
    payload["batches"] = batches
    canonical_json_dump(path, payload, pretty=True, drop_run_keys=False)


def _missing_endpoint_message() -> str:
    return build_guidance_message(
        what="OTLP endpoint is missing.",
        why="observability.yaml does not define otlp_config.endpoint.",
        fix="Set an endpoint before exporting traces.",
        example="otlp_config:\n  endpoint: \"http://localhost:4318/v1/traces\"",
    )


__all__ = ["OTLP_RETRY_FILENAME", "export_trace_runs"]
