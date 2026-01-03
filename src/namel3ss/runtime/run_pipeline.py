from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.ir import nodes as ir
from namel3ss.production_contract import apply_trace_hash, build_run_payload
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.storage.base import Storage
from namel3ss.security import redact_sensitive_payload, resolve_secret_values


@dataclass(frozen=True)
class FlowRunOutcome:
    payload: dict
    error: Exception | None
    runtime_theme: str | None


def build_flow_payload(
    program: ir.Program,
    flow_name: str,
    *,
    state: dict | None = None,
    input: dict | None = None,
    store: Storage | None = None,
    memory_manager: MemoryManager | None = None,
    runtime_theme: str | None = None,
    preference_store=None,
    preference_key: str | None = None,
    config: AppConfig | None = None,
    identity: dict | None = None,
    source: str | None = None,
    project_root: str | Path | None = None,
) -> FlowRunOutcome:
    state_value = state if isinstance(state, dict) else {}
    input_value = input if isinstance(input, dict) else {}
    root = project_root if project_root is not None else getattr(program, "project_root", None)
    try:
        result = execute_program_flow(
            program,
            flow_name,
            state=state_value,
            input=input_value,
            store=store,
            memory_manager=memory_manager,
            runtime_theme=runtime_theme,
            preference_store=preference_store,
            preference_key=preference_key,
            config=config,
            identity=identity,
        )
    except Exception as err:
        error_payload = _build_error_payload(err, source)
        payload = build_run_payload(
            ok=False,
            flow_name=flow_name,
            state=state_value,
            result=None,
            traces=[],
            project_root=root,
            error=err,
            error_payload=error_payload,
        )
        _attach_error_metadata(payload, err, _coerce_root(root))
        return FlowRunOutcome(payload=payload, error=err, runtime_theme=None)

    traces = [_trace_to_dict(trace) for trace in result.traces]
    ai_outputs = collect_ai_outputs(traces)
    payload = build_run_payload(
        ok=True,
        flow_name=flow_name,
        state=unwrap_ai_outputs(result.state, ai_outputs),
        result=unwrap_ai_outputs(result.last_value, ai_outputs),
        traces=traces,
        project_root=root,
    )
    return FlowRunOutcome(payload=payload, error=None, runtime_theme=result.runtime_theme)


def finalize_run_payload(payload: dict, secret_values: Iterable[str] | None = None) -> dict:
    resolved = resolve_secret_values(secret_values)
    redacted = redact_sensitive_payload(payload, resolved)  # type: ignore[assignment]
    if isinstance(redacted, dict):
        apply_trace_hash(redacted)
    return redacted


def collect_ai_outputs(traces: list[dict]) -> set[str]:
    outputs: set[str] = set()
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        output = trace.get("output")
        if isinstance(output, str):
            outputs.add(output)
    return outputs


def unwrap_ai_outputs(value: object, outputs: set[str]) -> object:
    if isinstance(value, dict):
        if set(value.keys()) == {"text"}:
            text = value.get("text")
            if isinstance(text, str) and text in outputs:
                return text
        return {key: unwrap_ai_outputs(val, outputs) for key, val in value.items()}
    if isinstance(value, list):
        return [unwrap_ai_outputs(item, outputs) for item in value]
    return value


def _build_error_payload(error: Exception, source: str | None) -> dict:
    if isinstance(error, Namel3ssError):
        return build_error_from_exception(error, kind="runtime", source=source)
    return build_error_payload(str(error), kind="runtime")


def _attach_error_metadata(payload: dict, error: Exception, project_root: Path | None) -> None:
    payload["error_type"] = error.__class__.__name__
    payload["error_message"] = str(error)
    error_step_id = _error_step_id(project_root)
    if error_step_id:
        payload["error_step_id"] = error_step_id


def _trace_to_dict(trace) -> dict:
    if hasattr(trace, "__dict__"):
        return trace.__dict__
    if isinstance(trace, dict):
        return dict(trace)
    return {"trace": trace}


def _error_step_id(project_root: Path | None) -> str | None:
    if project_root is None:
        return None
    path = project_root / ".namel3ss" / "execution" / "last.json"
    try:
        data = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return None
    steps = payload.get("execution_steps") if isinstance(payload, dict) else None
    if not isinstance(steps, list):
        return None
    for step in reversed(steps):
        if isinstance(step, dict) and step.get("kind") == "error" and step.get("id"):
            return str(step.get("id"))
    return None


def _coerce_root(value: str | Path | None) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


__all__ = [
    "FlowRunOutcome",
    "build_flow_payload",
    "collect_ai_outputs",
    "finalize_run_payload",
    "unwrap_ai_outputs",
]
