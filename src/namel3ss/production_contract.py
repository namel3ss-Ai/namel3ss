from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from namel3ss.determinism import apply_trace_hash, canonical_trace_json, normalize_traces, trace_hash
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.contract import build_error_entries
from namel3ss.outcome.api import load_outcome_pack
from namel3ss.traces.schema import TRACE_VERSION


PRODUCTION_CONTRACT_VERSION = "production.v0"
_ALLOWED_ERROR_CATEGORIES = {"parse", "runtime", "tool", "provider", "capability", "policy", "internal"}
_ALLOWED_STATUSES = {"ok", "partial", "error"}

def build_run_payload(
    *,
    ok: bool,
    flow_name: str | None,
    state: dict | None,
    result: object,
    traces: Iterable[Any] | None,
    project_root: str | Path | None = None,
    error: Exception | None = None,
    error_payload: dict | None = None,
) -> dict:
    root = _coerce_root(project_root)
    error_pack = _load_error_pack(root) if (not ok and root is not None) else None
    trace_items = list(traces or [])
    if not trace_items and error_pack and isinstance(error_pack.get("traces_tail"), list):
        trace_items = list(error_pack.get("traces_tail") or [])
    normalized_traces = normalize_traces(trace_items)
    contract = _build_contract(
        ok=ok,
        flow_name=flow_name,
        state=state,
        result=result,
        traces=normalized_traces,
        root=root,
        error=error,
        error_payload=error_payload,
        error_pack=error_pack,
    )
    payload = {
        "ok": bool(ok),
        "state": contract["state"],
        "result": contract["result"],
        "traces": normalized_traces,
        "contract": contract,
    }
    if contract.get("flow_name"):
        payload["flow_name"] = contract["flow_name"]
    if error_payload:
        for key, value in error_payload.items():
            if key == "ok":
                continue
            payload[key] = value
    return payload


def validate_run_contract(payload: dict) -> list[str]:
    issues: list[str] = []
    if not isinstance(payload, dict):
        return ["payload is not a dict"]
    ok = payload.get("ok")
    if not isinstance(ok, bool):
        issues.append("payload.ok must be a bool")
    contract = payload.get("contract")
    if not isinstance(contract, dict):
        issues.append("payload.contract must be a dict")
        return issues
    if contract.get("schema_version") != PRODUCTION_CONTRACT_VERSION:
        issues.append("contract.schema_version mismatch")
    if contract.get("trace_schema_version") != TRACE_VERSION:
        issues.append("contract.trace_schema_version mismatch")
    trace_hash_value = contract.get("trace_hash")
    if not isinstance(trace_hash_value, str) or not trace_hash_value:
        issues.append("contract.trace_hash must be a non-empty string")
    if contract.get("status") not in _ALLOWED_STATUSES:
        issues.append("contract.status must be ok, partial, or error")
    errors = contract.get("errors")
    if not isinstance(errors, list):
        issues.append("contract.errors must be a list")
        errors = []
    for idx, entry in enumerate(errors, start=1):
        if not isinstance(entry, dict):
            issues.append(f"contract.errors[{idx}] must be a dict")
            continue
        category = entry.get("category")
        code = entry.get("code")
        message = entry.get("message")
        if category not in _ALLOWED_ERROR_CATEGORIES:
            issues.append(f"contract.errors[{idx}].category invalid")
        if not isinstance(code, str) or not code:
            issues.append(f"contract.errors[{idx}].code missing")
        if not isinstance(message, str) or not message:
            issues.append(f"contract.errors[{idx}].message missing")
    traces = contract.get("traces")
    if not isinstance(traces, list):
        issues.append("contract.traces must be a list")
        traces = []
    for idx, trace in enumerate(traces, start=1):
        if not isinstance(trace, dict):
            issues.append(f"contract.traces[{idx}] must be a dict")
            continue
        if not isinstance(trace.get("type"), str) or not trace.get("type"):
            issues.append(f"contract.traces[{idx}].type missing")
        if not isinstance(trace.get("canonical_events"), list):
            issues.append(f"contract.traces[{idx}].canonical_events must be list")
        if not isinstance(trace.get("memory_events"), list):
            issues.append(f"contract.traces[{idx}].memory_events must be list")
    state = contract.get("state")
    if not isinstance(state, dict):
        issues.append("contract.state must be a dict")
    if "result" not in contract:
        issues.append("contract.result must be present (can be null)")
    memory = contract.get("memory")
    if not isinstance(memory, dict):
        issues.append("contract.memory must be a dict")
    else:
        events = memory.get("events")
        if not isinstance(events, list):
            issues.append("contract.memory.events must be a list")
        count = memory.get("count")
        if not isinstance(count, int):
            issues.append("contract.memory.count must be an int")
        elif isinstance(events, list) and count != len(events):
            issues.append("contract.memory.count must match events length")
    if isinstance(ok, bool):
        if ok and errors:
            issues.append("contract.errors must be empty when ok is true")
        if not ok and not errors:
            issues.append("contract.errors must be present when ok is false")
    return issues


def _build_contract(
    *,
    ok: bool,
    flow_name: str | None,
    state: dict | None,
    result: object,
    traces: list[dict],
    root: Path | None,
    error: Exception | None,
    error_payload: dict | None,
    error_pack: dict | None,
) -> dict:
    outcome = _load_outcome_pack(root)
    resolved_flow = _resolve_flow_name(flow_name, outcome, error_pack)
    status = _status_from_outcome(outcome, ok=ok)
    errors = _build_error_entries(error, error_payload, error_pack, project_root=root)
    memory_events = _collect_memory_events(traces)
    state_value = state if isinstance(state, dict) else {}
    contract = {
        "schema_version": PRODUCTION_CONTRACT_VERSION,
        "trace_schema_version": TRACE_VERSION,
        "status": status,
        "flow_name": resolved_flow,
        "errors": errors,
        "state": state_value,
        "result": result,
        "traces": traces,
        "memory": {"events": memory_events, "count": len(memory_events)},
        "outcome": outcome,
    }
    return contract


def _build_error_entries(
    error: Exception | None,
    error_payload: dict | None,
    error_pack: dict | None,
    project_root: Path | None = None,
) -> list[dict]:
    return build_error_entries(
        error=error,
        error_payload=error_payload,
        error_pack=error_pack,
        project_root=project_root,
    )


def _entry_from_error_pack(pack: dict) -> dict:
    info = pack.get("error") or {}
    boundary = info.get("boundary")
    kind = info.get("kind")
    category = _error_category(boundary=boundary, kind=kind, error_kind=None)
    if category != "capability" and _pack_indicates_capability(pack):
        category = "capability"
    where = info.get("where") if isinstance(info.get("where"), dict) else {}
    location = _location_from_where(where)
    message = str(info.get("what") or info.get("raw_message") or "Runtime error")
    code = str(info.get("error_id") or kind or "runtime_error")
    return {
        "category": category,
        "code": code,
        "message": message,
        "location": location,
        "details": info,
    }


def _entry_from_error_payload(payload: dict, error: Exception | None) -> dict:
    kind = payload.get("kind")
    category = _error_category(boundary=None, kind=None, error_kind=kind)
    details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
    error_id = details.get("error_id") if isinstance(details, dict) else None
    if not error_id and isinstance(error, Namel3ssError):
        err_details = error.details or {}
        error_id = err_details.get("error_id") if isinstance(err_details, dict) else None
    code = str(error_id or kind or error.__class__.__name__ if error else "runtime_error")
    message = str(payload.get("error") or payload.get("message") or "Runtime error")
    location = payload.get("location") if isinstance(payload.get("location"), dict) else None
    return {
        "category": category,
        "code": code,
        "message": message,
        "location": location,
        "details": details,
    }


def _entry_from_exception(error: Exception) -> dict:
    category = "runtime"
    if isinstance(error, Namel3ssError):
        details = error.details or {}
        error_id = details.get("error_id") if isinstance(details, dict) else None
        location = None
        if error.line is not None:
            location = {"line": error.line, "column": error.column}
        return {
            "category": category,
            "code": str(error_id or error.__class__.__name__),
            "message": str(error),
            "location": location,
            "details": details,
        }
    return {
        "category": category,
        "code": error.__class__.__name__,
        "message": str(error),
        "location": None,
        "details": {},
    }


def _pack_indicates_capability(pack: dict) -> bool:
    traces = pack.get("traces_tail")
    if not isinstance(traces, list):
        return False
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        if trace.get("type") == "capability_check" and trace.get("allowed") is False:
            return True
        if trace.get("error_type") == "CapabilityViolation":
            return True
    return False


def _error_category(*, boundary: str | None, kind: str | None, error_kind: object) -> str:
    if isinstance(error_kind, str) and error_kind:
        if error_kind == "parse":
            return "parse"
        if error_kind in {"tool", "tools"}:
            return "tool"
        if error_kind in {"provider", "ai_provider"}:
            return "provider"
        if error_kind in {"capability", "policy"}:
            return "capability"
    if boundary == "ai" and kind == "ai_provider_error":
        return "provider"
    if boundary == "tools" and kind == "tool_blocked":
        return "capability"
    if boundary == "tools":
        return "tool"
    if boundary == "fs":
        return "capability"
    return "runtime"


def _collect_memory_events(traces: list[dict]) -> list[dict]:
    events: list[dict] = []
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        trace_type = trace.get("type")
        if isinstance(trace_type, str) and "memory" in trace_type:
            events.append(trace)
        memory_events = trace.get("memory_events")
        if isinstance(memory_events, list):
            for event in memory_events:
                if isinstance(event, dict):
                    events.append(event)
    return events


def _load_error_pack(root: Path | None) -> dict | None:
    if root is None:
        return None
    path = root / ".namel3ss" / "errors" / "last.json"
    return _load_json(path)


def _load_outcome_pack(root: Path | None) -> dict | None:
    if root is None:
        return None
    path = root / ".namel3ss" / "outcome" / "last.json"
    pack = load_outcome_pack(path)
    return pack.as_dict() if pack else None


def _load_json(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _resolve_flow_name(flow_name: str | None, outcome: dict | None, error_pack: dict | None) -> str | None:
    if flow_name:
        return flow_name
    if outcome and isinstance(outcome.get("outcome"), dict):
        name = outcome["outcome"].get("flow_name")
        if isinstance(name, str) and name:
            return name
    if error_pack and isinstance(error_pack.get("summary"), dict):
        name = error_pack["summary"].get("flow_name")
        if isinstance(name, str) and name:
            return name
    return None


def _status_from_outcome(outcome: dict | None, *, ok: bool) -> str:
    if outcome and isinstance(outcome.get("outcome"), dict):
        status = outcome["outcome"].get("status")
        if isinstance(status, str) and status in _ALLOWED_STATUSES:
            return status
    return "ok" if ok else "error"


def _location_from_where(where: dict) -> dict | None:
    line = where.get("line")
    column = where.get("column")
    if line is None and column is None:
        return None
    return {"line": line, "column": column}


def _coerce_root(value: str | Path | None) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


__all__ = [
    "PRODUCTION_CONTRACT_VERSION",
    "build_run_payload",
    "canonical_trace_json",
    "normalize_traces",
    "trace_hash",
    "apply_trace_hash",
    "validate_run_contract",
]
