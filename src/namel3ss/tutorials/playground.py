from __future__ import annotations

import multiprocessing
from pathlib import Path
from tempfile import TemporaryDirectory

from namel3ss.module_loader import load_project
from namel3ss.purity import is_pure
from namel3ss.runtime.run_pipeline import build_flow_payload

DEFAULT_PLAYGROUND_TIMEOUT_SECONDS = 5.0
MAX_PLAYGROUND_TIMEOUT_SECONDS = 30.0
_SPAWN_TIMEOUT_GRACE_SECONDS = 3.0


def check_snippet(source: str) -> dict[str, object]:
    normalized = _normalize_source(source)
    try:
        with TemporaryDirectory(prefix="n3-playground-") as tmp:
            app_path = Path(tmp) / "app.ai"
            app_path.write_text(normalized, encoding="utf-8")
            project = load_project(app_path)
        flow_names = sorted({flow.name for flow in project.program.flows})
        pure_flows = sorted({flow.name for flow in project.program.flows if is_pure(getattr(flow, "purity", None))})
        return {"ok": True, "flow_count": len(flow_names), "flows": flow_names, "pure_flows": pure_flows}
    except Exception as err:
        return {"ok": False, "error": str(err), "flow_count": 0, "flows": [], "pure_flows": []}


def run_snippet(
    source: str,
    *,
    flow_name: str | None = None,
    input_payload: dict | None = None,
    timeout_seconds: float = DEFAULT_PLAYGROUND_TIMEOUT_SECONDS,
) -> dict[str, object]:
    context = multiprocessing.get_context("spawn")
    effective_timeout = float(timeout_seconds)
    if context.get_start_method() == "spawn":
        effective_timeout += _SPAWN_TIMEOUT_GRACE_SECONDS
    queue = context.Queue()
    process = context.Process(
        target=_run_worker,
        args=(queue, source, flow_name, input_payload if isinstance(input_payload, dict) else {}),
    )
    process.start()
    process.join(effective_timeout)
    if process.is_alive():
        process.terminate()
        process.join()
        return {
            "ok": False,
            "error": f"Playground run exceeded timeout ({timeout_seconds:.1f}s).",
            "flow_name": flow_name,
            "result": None,
        }
    if queue.empty():
        return {"ok": False, "error": "Playground worker returned no result.", "flow_name": flow_name, "result": None}
    payload = queue.get()
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Playground worker returned invalid payload.", "flow_name": flow_name, "result": None}
    return payload


def _run_worker(queue, source: str, flow_name: str | None, input_payload: dict) -> None:  # noqa: ANN001
    normalized = _normalize_source(source)
    try:
        with TemporaryDirectory(prefix="n3-playground-run-") as tmp:
            app_path = Path(tmp) / "app.ai"
            app_path.write_text(normalized, encoding="utf-8")
            project = load_project(app_path)
            selected = _resolve_flow(project.program, flow_name)
            if selected is None:
                queue.put(
                    {
                        "ok": False,
                        "error": "No runnable pure flow found in snippet.",
                        "flow_name": flow_name,
                        "result": None,
                    }
                )
                return
            outcome = build_flow_payload(project.program, selected, input=input_payload)
            queue.put(
                {
                    "ok": bool(outcome.payload.get("ok", False)),
                    "flow_name": selected,
                    "result": outcome.payload.get("result"),
                    "payload": outcome.payload,
                }
            )
    except Exception as err:
        queue.put({"ok": False, "error": str(err), "flow_name": flow_name, "result": None})


def _resolve_flow(program, flow_name: str | None) -> str | None:  # noqa: ANN001
    flows = sorted(program.flows, key=lambda item: item.name)
    if flow_name:
        for flow in flows:
            if flow.name == flow_name and is_pure(getattr(flow, "purity", None)):
                return flow.name
        return None
    for flow in flows:
        if is_pure(getattr(flow, "purity", None)):
            return flow.name
    return None


def _normalize_source(source: str) -> str:
    text = source.replace("\r\n", "\n").replace("\r", "\n")
    stripped = text.lstrip()
    if not stripped:
        return 'spec is "1.0"\n\nflow "demo": purity is "pure"\n  return "ok"\n'
    if stripped.startswith("spec "):
        return text if text.endswith("\n") else text + "\n"
    merged = 'spec is "1.0"\n\n' + text
    return merged if merged.endswith("\n") else merged + "\n"


__all__ = [
    "DEFAULT_PLAYGROUND_TIMEOUT_SECONDS",
    "MAX_PLAYGROUND_TIMEOUT_SECONDS",
    "check_snippet",
    "run_snippet",
]
