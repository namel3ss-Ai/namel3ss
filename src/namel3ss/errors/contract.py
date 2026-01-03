from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.runtime.normalize import stable_truncate
from namel3ss.secrets import collect_secret_values, redact_payload, redact_text


ERROR_CATEGORIES = (
    "parse",
    "runtime",
    "tool",
    "provider",
    "capability",
    "policy",
    "internal",
)

_KIND_CATEGORY_MAP = {
    "parse": "parse",
    "runtime": "runtime",
    "tool": "tool",
    "tools": "tool",
    "provider": "provider",
    "ai_provider": "provider",
    "capability": "capability",
    "policy": "policy",
    "internal": "internal",
    "engine": "internal",
    "manifest": "runtime",
    "diagnostics": "runtime",
}

_DEFAULT_CODES = {
    "parse": "parse_error",
    "runtime": "runtime_error",
    "tool": "tool_error",
    "provider": "provider_error",
    "capability": "capability_denied",
    "policy": "policy_denied",
    "internal": "internal_error",
}

_FALLBACK_MESSAGES = {
    "parse": "Parse error.",
    "runtime": "Runtime error.",
    "tool": "Tool error.",
    "provider": "Provider error.",
    "capability": "Capability error.",
    "policy": "Policy error.",
    "internal": "Internal error.",
}

_OBJECT_ID_RE = re.compile(r"0x[0-9a-fA-F]+")

_POLICY_REASONS = {"policy_denied", "unknown_tool", "missing_binding", "pack_unavailable_or_unverified"}

_SENSITIVE_KEY_MARKERS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "access_key",
    "authorization",
    "auth",
    "credential",
)

_PATH_KEY_SUFFIXES = ("_path", "_file")
_PATH_KEY_NAMES = {"file", "path", "app_path", "project_root"}


def build_error_entries(
    *,
    error: Exception | None,
    error_payload: dict | None,
    error_pack: dict | None,
    project_root: str | Path | None = None,
    secret_values: Iterable[str] | None = None,
) -> list[dict]:
    entry = build_error_entry(
        error=error,
        error_payload=error_payload,
        error_pack=error_pack,
        project_root=project_root,
        secret_values=secret_values,
    )
    return [entry] if entry else []


def build_error_entry(
    *,
    error: Exception | None,
    error_payload: dict | None,
    error_pack: dict | None,
    project_root: str | Path | None = None,
    secret_values: Iterable[str] | None = None,
) -> dict:
    if isinstance(error_pack, dict):
        entry = _entry_from_error_pack(error_pack)
    elif isinstance(error_payload, dict):
        entry = _entry_from_error_payload(error_payload, error)
    elif isinstance(error, Exception):
        entry = _entry_from_exception(error)
    else:
        return {}
    resolved_secrets = _resolve_secret_values(secret_values)
    return _normalize_entry(entry, project_root=project_root, secret_values=resolved_secrets)


def _entry_from_error_pack(pack: dict) -> dict:
    info = pack.get("error") or {}
    boundary = info.get("boundary")
    kind = info.get("kind")
    error_id = info.get("error_id")
    where = info.get("where") if isinstance(info.get("where"), dict) else {}
    location = _location_from_where(where)
    message = str(info.get("what") or info.get("raw_message") or "Runtime error")
    hint = _first_text(info.get("why"))
    remediation = _first_text(info.get("fix"))
    details = _pack_details(info)
    traces_tail = pack.get("traces_tail") if isinstance(pack.get("traces_tail"), list) else []
    category = _category_from_pack(boundary=boundary, kind=kind, traces_tail=traces_tail)
    code = str(error_id or kind or _DEFAULT_CODES.get(category, "runtime_error"))
    trace_ref = str(error_id) if isinstance(error_id, str) and error_id else None
    return {
        "category": category,
        "code": code,
        "message": message,
        "location": location,
        "hint": hint,
        "remediation": remediation,
        "trace_ref": trace_ref,
        "details": details,
    }


def _entry_from_error_payload(payload: dict, error: Exception | None) -> dict:
    if isinstance(payload.get("error_entry"), dict):
        return dict(payload["error_entry"])
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict):
            return dict(first)
    kind = payload.get("kind")
    details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
    code = _payload_code(details, error, kind)
    message = str(payload.get("message") or payload.get("error") or "Runtime error")
    location = payload.get("location") if isinstance(payload.get("location"), dict) else None
    parsed = _parse_guidance_message(message)
    hint = parsed.get("why")
    remediation = parsed.get("fix")
    if parsed.get("what"):
        message = parsed["what"]
    category = _category_from_kind(kind)
    trace_ref = _trace_ref_from_details(details, error)
    return {
        "category": category,
        "code": code,
        "message": message,
        "location": location,
        "hint": hint,
        "remediation": remediation,
        "trace_ref": trace_ref,
        "details": details,
    }


def _entry_from_exception(error: Exception) -> dict:
    details = {}
    if isinstance(error, Namel3ssError):
        details = error.details or {}
    message = _error_message(error)
    parsed = _parse_guidance_message(message)
    hint = parsed.get("why")
    remediation = parsed.get("fix")
    if parsed.get("what"):
        message = parsed["what"]
    location = None
    if isinstance(error, Namel3ssError) and (error.line is not None or error.column is not None):
        location = {"line": error.line, "column": error.column}
    code = _payload_code(details, error, None)
    category = _category_from_kind(details.get("category") if isinstance(details, dict) else None)
    trace_ref = _trace_ref_from_details(details, error)
    return {
        "category": category,
        "code": code,
        "message": message,
        "location": location,
        "hint": hint,
        "remediation": remediation,
        "trace_ref": trace_ref,
        "details": details,
    }


def _normalize_entry(entry: dict, *, project_root: str | Path | None, secret_values: list[str]) -> dict:
    normalized: dict[str, object] = {}
    category = entry.get("category")
    normalized["category"] = category if category in ERROR_CATEGORIES else "runtime"
    code = entry.get("code")
    normalized["code"] = str(code) if code else _DEFAULT_CODES.get(normalized["category"], "runtime_error")
    message = entry.get("message")
    normalized_message = _normalize_text(message, project_root, secret_values)
    if not normalized_message:
        normalized_message = _FALLBACK_MESSAGES.get(normalized["category"], "Runtime error.")
    normalized["message"] = normalized_message
    location = _normalize_location(entry.get("location"), project_root)
    normalized["location"] = location
    hint = entry.get("hint")
    if hint:
        normalized["hint"] = _normalize_text(hint, project_root, secret_values)
    remediation = entry.get("remediation")
    if remediation:
        normalized["remediation"] = _normalize_text(remediation, project_root, secret_values)
    trace_ref = entry.get("trace_ref")
    if isinstance(trace_ref, str) and trace_ref:
        normalized["trace_ref"] = trace_ref
    details = entry.get("details")
    if isinstance(details, dict) and details:
        normalized["details"] = _normalize_payload(details, project_root, secret_values)
    return normalized


def _normalize_text(value: object, project_root: str | Path | None, secret_values: list[str]) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = _strip_traceback(text)
    text = _OBJECT_ID_RE.sub("0x<id>", text)
    text = _normalize_paths(text, project_root)
    text = " ".join(text.split())
    text = redact_text(text, secret_values)
    return stable_truncate(text, 240)


def _normalize_payload(value: object, project_root: str | Path | None, secret_values: list[str]) -> object:
    if isinstance(value, dict):
        cleaned: dict[str, object] = {}
        for key in sorted(value.keys(), key=lambda item: str(item)):
            key_text = str(key)
            child = value[key]
            if isinstance(child, str) and _is_path_key(key_text):
                cleaned[key_text] = _normalize_file(child, project_root) or _normalize_text(child, project_root, secret_values)
            else:
                cleaned[key_text] = _normalize_payload(child, project_root, secret_values)
        redacted = redact_payload(cleaned, secret_values)
        return _redact_sensitive_keys(redacted)
    if isinstance(value, list):
        return [ _normalize_payload(item, project_root, secret_values) for item in value ]
    if isinstance(value, str):
        return _normalize_text(value, project_root, secret_values)
    return value


def _normalize_location(location: object, project_root: str | Path | None) -> dict | None:
    if not isinstance(location, dict):
        return None
    line = location.get("line")
    column = location.get("column")
    file_value = location.get("file")
    normalized: dict[str, object] = {}
    if isinstance(line, int):
        normalized["line"] = line
    if isinstance(column, int):
        normalized["column"] = column
    file_path = _normalize_file(file_value, project_root)
    if file_path:
        normalized["file"] = file_path
    return normalized or None


def _normalize_file(value: object, project_root: str | Path | None) -> str | None:
    if value is None:
        return None
    try:
        path = Path(str(value))
    except Exception:
        return None
    if project_root is None:
        return path.name or path.as_posix()
    if project_root:
        root = _coerce_root(project_root)
        if root is not None:
            try:
                return path.resolve().relative_to(root.resolve()).as_posix()
            except Exception:
                pass
    return path.as_posix()


def _category_from_pack(boundary: object, kind: object, traces_tail: list[dict]) -> str:
    if _pack_is_policy(traces_tail):
        return "policy"
    if _pack_is_capability(traces_tail):
        return "capability"
    if boundary == "ai" and kind == "ai_provider_error":
        return "provider"
    if boundary == "tools":
        return "tool"
    return "runtime"


def _pack_is_policy(traces_tail: list[dict]) -> bool:
    for trace in traces_tail:
        if not isinstance(trace, dict):
            continue
        if trace.get("type") == "capability_check" and trace.get("reason") == "policy_denied":
            return True
        if trace.get("type") == "tool_call" and trace.get("reason") in _POLICY_REASONS:
            return True
    return False


def _pack_is_capability(traces_tail: list[dict]) -> bool:
    for trace in traces_tail:
        if not isinstance(trace, dict):
            continue
        if trace.get("type") == "capability_check" and trace.get("allowed") is False:
            return True
        if trace.get("error_type") == "CapabilityViolation":
            return True
    return False


def _payload_code(details: dict, error: Exception | None, kind: object) -> str:
    error_id = None
    if isinstance(details, dict):
        error_id = details.get("error_id") or details.get("code")
    if not error_id and isinstance(error, Namel3ssError):
        err_details = error.details or {}
        error_id = err_details.get("error_id") if isinstance(err_details, dict) else None
    if error_id:
        return str(error_id)
    category = _category_from_kind(kind)
    return _DEFAULT_CODES.get(category, "runtime_error")


def _category_from_kind(kind: object) -> str:
    if isinstance(kind, str):
        return _KIND_CATEGORY_MAP.get(kind, "runtime")
    return "runtime"


def _location_from_where(where: dict) -> dict | None:
    line = where.get("line")
    column = where.get("column")
    if line is None and column is None:
        return None
    return {"line": line, "column": column}


def _pack_details(info: dict) -> dict:
    details = {
        "error_id": info.get("error_id"),
        "boundary": info.get("boundary"),
        "kind": info.get("kind"),
        "where": info.get("where"),
        "example": info.get("example"),
    }
    return {key: value for key, value in details.items() if value is not None}


def _trace_ref_from_details(details: dict, error: Exception | None) -> str | None:
    if isinstance(details, dict):
        for key in ("trace_ref", "error_step_id", "error_id"):
            value = details.get(key)
            if isinstance(value, str) and value:
                return value
    if isinstance(error, Namel3ssError):
        err_details = error.details or {}
        if isinstance(err_details, dict):
            value = err_details.get("error_id")
            if isinstance(value, str) and value:
                return value
    return None


def _first_text(value: object) -> str | None:
    if isinstance(value, (list, tuple)) and value:
        first = value[0]
        return str(first) if first else None
    if isinstance(value, str):
        return value
    return None


def _parse_guidance_message(message: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in str(message).splitlines():
        line = raw_line.strip()
        if line.startswith("What happened:"):
            parsed["what"] = line[len("What happened:") :].strip()
        elif line.startswith("Why:"):
            parsed["why"] = line[len("Why:") :].strip()
        elif line.startswith("Fix:"):
            parsed["fix"] = line[len("Fix:") :].strip()
        elif line.startswith("Example:"):
            parsed["example"] = line[len("Example:") :].strip()
    return parsed


def _strip_traceback(text: str) -> str:
    if "Traceback" not in text:
        return text
    return text.split("Traceback", 1)[0].strip()


def _normalize_paths(text: str, project_root: str | Path | None) -> str:
    root = _coerce_root(project_root)
    if root is None:
        return text
    root_text = root.as_posix()
    if root_text and root_text in text:
        return text.replace(root_text, "<project_root>")
    return text


def _coerce_root(value: str | Path | None) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


def _error_message(err: Exception) -> str:
    if isinstance(err, Namel3ssError):
        return err.message
    return str(err)


def _resolve_secret_values(secret_values: Iterable[str] | None) -> list[str]:
    if secret_values is None:
        return collect_secret_values()
    return list(secret_values)


def _redact_sensitive_keys(value: object) -> object:
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, val in value.items():
            if _is_sensitive_key(key):
                redacted[str(key)] = "***REDACTED***"
            else:
                redacted[str(key)] = _redact_sensitive_keys(val)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive_keys(item) for item in value]
    return value


def _is_sensitive_key(key: object) -> bool:
    text = str(key).lower()
    return any(marker in text for marker in _SENSITIVE_KEY_MARKERS)


def _is_path_key(key: str) -> bool:
    text = key.lower()
    if text in _PATH_KEY_NAMES:
        return True
    return text.endswith(_PATH_KEY_SUFFIXES)


__all__ = ["ERROR_CATEGORIES", "build_error_entries", "build_error_entry"]
