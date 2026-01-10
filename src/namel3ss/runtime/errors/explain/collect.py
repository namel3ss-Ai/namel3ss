from __future__ import annotations

import json
from pathlib import Path

from namel3ss.runtime.errors.explain.model import ErrorState, ErrorWhere


def collect_last_error(project_root: Path) -> ErrorState | None:
    run_last = _load_json(project_root / ".namel3ss" / "run" / "last.json")
    run_payload = run_last if isinstance(run_last, dict) else None
    if run_payload and bool(run_payload.get("ok", True)):
        return None

    error_pack = _load_json(project_root / ".namel3ss" / "errors" / "last.json")
    runtime_pack = _runtime_error_pack(error_pack)

    if not run_payload and not runtime_pack:
        return None

    flow_name = None
    if run_payload and run_payload.get("flow_name"):
        flow_name = run_payload.get("flow_name")
    elif runtime_pack and runtime_pack.get("summary"):
        summary = runtime_pack.get("summary") or {}
        flow_name = summary.get("flow_name")
    flow_name = str(flow_name) if flow_name else None

    error_type, error_message = _extract_run_error(run_payload)
    error_entry = _error_entry(run_payload)
    error_step_id = None
    if run_payload and run_payload.get("error_step_id"):
        error_step_id = run_payload.get("error_step_id")
    error_step_id = error_step_id or _error_step_id(project_root)

    tools_last = _load_json(project_root / ".namel3ss" / "tools" / "last.json")
    tool_name, tool_kind = _tool_error(tools_last)
    kind = _infer_kind(error_type, error_message, tool_kind, error_entry, runtime_pack)

    what, why = _resolve_context(error_message, error_entry, runtime_pack)
    if not what:
        what = _first_line(error_message) or str(error_type or "error")
    if not why:
        why = _fallback_why(error_message, error_type)

    where = ErrorWhere(flow_name=flow_name, step_id=error_step_id, tool_name=tool_name)
    details = _build_details(error_type, error_message, error_step_id, error_entry, runtime_pack)
    return ErrorState(
        id="error:1",
        kind=kind,
        where=where,
        what=what,
        why=why,
        details=details,
        impact=[],
        recoverable=False,
        recovery_options=[],
    )


def _tool_error(tools_last: dict | None) -> tuple[str | None, str | None]:
    if not isinstance(tools_last, dict):
        return None, None
    entries = _tool_entries(tools_last)
    for entry in entries:
        if entry.get("result") == "blocked":
            return entry.get("tool"), "permission"
    for entry in entries:
        if entry.get("result") == "error":
            return entry.get("tool"), "execution"
    return None, None


def _infer_kind(
    error_type: str | None,
    error_message: str | None,
    tool_kind: str | None,
    error_entry: dict | None,
    runtime_pack: dict | None,
) -> str:
    if runtime_pack:
        kind = _kind_from_runtime_pack(runtime_pack)
        if kind:
            return kind
    if error_entry:
        kind = _kind_from_error_entry(error_entry)
        if kind:
            return kind
    if tool_kind:
        return tool_kind
    if error_type == "CapabilityViolation":
        return "permission"
    if _message_mentions_identity(error_message):
        return "permission"
    if _message_mentions_memory(error_message):
        return "memory"
    if error_type:
        return "execution"
    return "unknown"


def _message_mentions_identity(error_message: str | None) -> bool:
    if not error_message:
        return False
    lowered = error_message.lower()
    return (
        "identity" in lowered
        or "tenant" in lowered
        or "n3_identity" in lowered
        or "access is not permitted" in lowered
        or "requires condition evaluated to false" in lowered
    )


def _error_step_id(project_root: Path) -> str | None:
    execution = _load_json(project_root / ".namel3ss" / "execution" / "last.json")
    if not isinstance(execution, dict):
        return None
    steps = execution.get("execution_steps") or []
    if not isinstance(steps, list):
        return None
    for step in reversed(steps):
        if isinstance(step, dict) and step.get("kind") == "error" and step.get("id"):
            return str(step.get("id"))
    return None


def _tool_entries(tools_last: dict) -> list[dict]:
    if any(key in tools_last for key in ("allowed", "blocked", "errors")):
        entries: list[dict] = []
        for key in ("allowed", "blocked", "errors"):
            values = tools_last.get(key) or []
            if isinstance(values, list):
                entries.extend([item for item in values if isinstance(item, dict)])
        return entries
    decisions = tools_last.get("decisions") or []
    if not isinstance(decisions, list):
        return []
    entries: list[dict] = []
    for entry in decisions:
        if isinstance(entry, dict):
            entries.append(_entry_from_decision(entry))
    return entries


def _entry_from_decision(entry: dict) -> dict:
    tool_name = str(entry.get("tool_name") or "tool")
    status = str(entry.get("status") or "")
    permission = entry.get("permission") if isinstance(entry.get("permission"), dict) else {}
    reasons = permission.get("reasons") if isinstance(permission.get("reasons"), list) else []
    capabilities = permission.get("capabilities_used") if isinstance(permission.get("capabilities_used"), list) else []
    reason = str(reasons[0]) if reasons else "unknown"
    capability = str(capabilities[0]) if capabilities else "none"
    result = status if status in {"ok", "blocked", "error"} else "ok"
    return {
        "tool": tool_name,
        "decision": "blocked" if result == "blocked" else "allowed",
        "capability": capability,
        "reason": reason,
        "result": result,
    }


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _runtime_error_pack(payload: dict | None) -> dict | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("api_version") == "errors.v1":
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    if not error.get("error_id"):
        return None
    return payload


def _extract_run_error(run_payload: dict | None) -> tuple[str | None, str | None]:
    if not isinstance(run_payload, dict):
        return None, None
    error_type = run_payload.get("error_type")
    error_message = run_payload.get("error_message")
    error = run_payload.get("error")
    if isinstance(error, dict):
        if error_type is None:
            error_type = error.get("kind")
        if error_message is None:
            error_message = error.get("message")
    elif isinstance(error, str) and not error_message:
        error_message = error
    if not error_message and isinstance(run_payload.get("message"), str):
        error_message = run_payload.get("message")
    return _coerce_str(error_type), _coerce_str(error_message)


def _error_entry(run_payload: dict | None) -> dict | None:
    if not isinstance(run_payload, dict):
        return None
    entry = run_payload.get("error_entry")
    if isinstance(entry, dict):
        return entry
    errors = run_payload.get("errors")
    if isinstance(errors, list):
        for item in errors:
            if isinstance(item, dict):
                return item
    contract = run_payload.get("contract")
    if isinstance(contract, dict):
        contract_errors = contract.get("errors")
        if isinstance(contract_errors, list):
            for item in contract_errors:
                if isinstance(item, dict):
                    return item
    return None


def _resolve_context(
    error_message: str | None,
    error_entry: dict | None,
    runtime_pack: dict | None,
) -> tuple[str | None, str | None]:
    if runtime_pack:
        runtime_error = runtime_pack.get("error") or {}
        what = _coerce_str(runtime_error.get("what"))
        why = _join_lines(runtime_error.get("why"))
        if what or why:
            return what, why
    parts = _parse_guidance_parts(error_message)
    if not parts and error_message:
        parts = _parse_runtime_plain_parts(error_message)
    if parts:
        what = _coerce_str(parts.get("what"))
        why = _join_lines(parts.get("why"))
        if what or why:
            return what, why
    if error_entry:
        return _coerce_str(error_entry.get("message")), _coerce_str(error_entry.get("hint"))
    return None, None


def _parse_guidance_parts(message: str | None) -> dict[str, object]:
    if not message:
        return {}
    what = None
    why = None
    fixes: list[str] = []
    for line in str(message).splitlines():
        line = line.strip()
        if line.startswith("What happened:"):
            what = line.replace("What happened:", "").strip()
        elif line.startswith("Why:"):
            why = line.replace("Why:", "").strip()
        elif line.startswith("Fix:"):
            fix = line.replace("Fix:", "").strip()
            if fix:
                fixes.append(fix)
    return {"what": what, "why": [why] if why else [], "fix": fixes} if what or why or fixes else {}


def _parse_runtime_plain_parts(message: str) -> dict[str, object]:
    sections: dict[str, list[str]] = {"what": [], "why": [], "fix": []}
    current: str | None = None
    summary = None
    for raw_line in str(message).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if lower == "what happened":
            current = "what"
            continue
        if lower == "why":
            current = "why"
            continue
        if lower in {"how to fix", "fix this error"}:
            current = "fix"
            continue
        if lower in {"where", "error id"}:
            current = None
            continue
        if line.startswith("error:"):
            summary = line.replace("error:", "", 1).strip()
            continue
        if line.startswith("- "):
            if current:
                sections[current].append(line.replace("- ", "", 1).strip())
            continue
    what = summary or (sections["what"][0] if sections["what"] else None)
    return {"what": what, "why": sections["why"], "fix": sections["fix"]} if what or sections["why"] or sections["fix"] else {}


def _kind_from_runtime_pack(pack: dict) -> str | None:
    error = pack.get("error") if isinstance(pack, dict) else None
    if not isinstance(error, dict):
        return None
    boundary = _coerce_str(error.get("boundary"))
    kind = _coerce_str(error.get("kind"))
    raw_message = _coerce_str(error.get("raw_message"))
    what = _coerce_str(error.get("what"))
    if _message_mentions_identity(raw_message) or _message_mentions_identity(what):
        return "permission"
    if boundary == "tools" and kind == "tool_blocked":
        return "permission"
    if boundary == "tools":
        return "execution"
    if boundary == "memory" or (kind and kind.startswith("memory_")):
        return "memory"
    if boundary == "ai":
        return "execution"
    if boundary == "store":
        return "execution"
    if boundary == "theme":
        return "execution"
    if boundary == "fs":
        return "permission"
    if boundary == "engine":
        return "execution"
    return None


def _kind_from_error_entry(entry: dict) -> str | None:
    category = _coerce_str(entry.get("category"))
    if not category:
        return None
    if category == "parse":
        return "validation"
    if category in {"capability", "policy"}:
        return "permission"
    if category in {"tool", "provider", "runtime", "internal"}:
        return "execution"
    return None


def _message_mentions_memory(error_message: str | None) -> bool:
    if not error_message:
        return False
    return "memory" in error_message.lower()


def _build_details(
    error_type: str | None,
    error_message: str | None,
    error_step_id: str | None,
    error_entry: dict | None,
    runtime_pack: dict | None,
) -> dict:
    details = {
        "error_type": error_type,
        "error_message": error_message,
        "error_step_id": error_step_id,
    }
    if error_entry:
        category = _coerce_str(error_entry.get("category"))
        code = _coerce_str(error_entry.get("code"))
        if category:
            details["error_category"] = category
        if code:
            details["error_code"] = code
    if runtime_pack:
        error = runtime_pack.get("error") or {}
        error_id = _coerce_str(error.get("error_id"))
        if error_id:
            details["error_id"] = error_id
    return details


def _join_lines(value: object) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        if not cleaned:
            return None
        if len(cleaned) == 1:
            return cleaned[0]
        return "; ".join(cleaned)
    return str(value).strip() or None


def _first_line(message: str | None) -> str | None:
    if not message:
        return None
    for line in str(message).splitlines():
        stripped = line.strip()
        if stripped:
            if stripped.startswith("error:"):
                stripped = stripped.replace("error:", "", 1).strip()
            return stripped
    return None


def _fallback_why(error_message: str | None, error_type: str | None) -> str | None:
    if error_message:
        return _first_line(error_message)
    if error_type:
        return f"Raised {error_type}."
    return "Error details were not recorded."


def _coerce_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


__all__ = ["collect_last_error"]
