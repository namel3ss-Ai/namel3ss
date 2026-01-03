from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.runtime.classify import classify_error
from namel3ss.errors.runtime.ids import build_error_id
from namel3ss.errors.runtime.model import ErrorPack, Namel3ssRuntimeError, RuntimeWhere
from namel3ss.errors.runtime.normalize import normalize_error, normalize_traces, write_error_artifacts
from namel3ss.errors.runtime.render_plain import render_error_plain, render_fix_text
from namel3ss.secrets import collect_secret_values, redact_text


_TEMPLATES = {
    "runtime.tools.blocked": {
        "what": "Tool call was blocked.",
        "why": ("Tool execution was blocked.",),
        "fix": ("Allow the required capability or remove the tool call.",),
        "example": None,
    },
    "runtime.tools.failed": {
        "what": "Tool call failed.",
        "why": ("The tool call did not complete.",),
        "fix": ("Check tool bindings and inputs.",),
        "example": None,
    },
    "runtime.ai.provider_error": {
        "what": "AI provider error.",
        "why": ("The AI provider returned an error.",),
        "fix": ("Check the AI provider configuration.",),
        "example": None,
    },
    "runtime.ai.failed": {
        "what": "AI call failed.",
        "why": ("The AI call did not complete.",),
        "fix": ("Check the AI profile and inputs.",),
        "example": None,
    },
    "runtime.store.commit_failed": {
        "what": "Store commit failed.",
        "why": ("The storage commit did not complete.",),
        "fix": ("Check storage configuration and retry.",),
        "example": None,
    },
    "runtime.store.rollback_failed": {
        "what": "Store rollback failed.",
        "why": ("The storage rollback did not complete.",),
        "fix": ("Check storage health and retry.",),
        "example": None,
    },
    "runtime.store.failed": {
        "what": "Store operation failed.",
        "why": ("The storage operation did not complete.",),
        "fix": ("Check storage configuration.",),
        "example": None,
    },
    "runtime.memory.persist_failed": {
        "what": "Memory persistence failed.",
        "why": ("Memory could not be saved.",),
        "fix": ("Check the project folder permissions.",),
        "example": None,
    },
    "runtime.memory.failed": {
        "what": "Memory operation failed.",
        "why": ("The memory operation did not complete.",),
        "fix": ("Check memory configuration.",),
        "example": None,
    },
    "runtime.theme.failed": {
        "what": "Theme resolution failed.",
        "why": ("Theme could not be resolved.",),
        "fix": ("Check the theme settings.",),
        "example": None,
    },
    "runtime.fs.failed": {
        "what": "Filesystem operation failed.",
        "why": ("The filesystem operation did not complete.",),
        "fix": ("Check file permissions and paths.",),
        "example": None,
    },
    "runtime.engine.error": {
        "what": "Runtime error.",
        "why": ("The engine raised an error.",),
        "fix": ("Review the error message and try again.",),
        "example": None,
    },
}


def build_error_pack(
    *,
    boundary: str,
    err: Exception,
    where: RuntimeWhere,
    traces: list[dict] | None = None,
) -> ErrorPack:
    boundary = boundary or "engine"
    kind, template_key = classify_error(boundary, err)
    error_id = build_error_id(boundary, kind, where, template_key)
    raw_message = _raw_message(err)
    secret_values = _secret_values(err)
    redacted_message = _strip_traceback(redact_text(raw_message, secret_values))

    template = _TEMPLATES.get(template_key, _TEMPLATES["runtime.engine.error"])
    parsed = _parse_guidance_message(redacted_message)
    template_what = str(template.get("what") or "Runtime error.")
    template_why = tuple(template.get("why", ()))
    template_fix = tuple(template.get("fix", ()))
    template_example = template.get("example")
    if parsed:
        what = parsed.get("what") or template_what
        why = (parsed["why"],) if parsed.get("why") else template_why
        fix = (parsed["fix"],) if parsed.get("fix") else template_fix
        example = parsed.get("example") or template_example
    else:
        what = template_what
        why = template_why
        fix = template_fix
        example = template_example
        if redacted_message:
            why = tuple(list(why) + [f"Error message: {redacted_message}"])

    runtime_error = Namel3ssRuntimeError(
        error_id=error_id,
        kind=kind,
        boundary=boundary,
        what=what,
        why=why,
        fix=fix,
        example=example,
        where=where,
        raw_message=redacted_message,
    )
    normalized = normalize_error(runtime_error)
    traces_tail = normalize_traces(traces or [], secret_values=secret_values)
    summary = {
        "ok": False,
        "flow_name": where.flow_name,
        "boundary": normalized.boundary,
        "kind": normalized.kind,
    }
    pack = ErrorPack(error=normalized, summary=summary, traces_tail=traces_tail)

    root = _project_root(err)
    if root is not None:
        plain = render_error_plain(pack)
        fix_text = render_fix_text(pack)
        try:
            write_error_artifacts(root, pack, plain, fix_text)
        except Exception:
            pass

    return pack


def _raw_message(err: Exception) -> str:
    if isinstance(err, Namel3ssError):
        return err.message
    return str(err)


def _secret_values(err: Exception) -> list[str]:
    values = getattr(err, "__namel3ss_secret_values__", None)
    if isinstance(values, list):
        return values
    return collect_secret_values()


def _project_root(err: Exception) -> Path | None:
    value = getattr(err, "__namel3ss_project_root__", None)
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


def _parse_guidance_message(message: str) -> dict[str, str] | None:
    if not message:
        return None
    parsed: dict[str, str] = {}
    current_key: str | None = None
    for raw_line in str(message).splitlines():
        line = raw_line.strip()
        matched = False
        for key, prefix in (
            ("what", "What happened:"),
            ("why", "Why:"),
            ("fix", "Fix:"),
            ("example", "Example:"),
        ):
            if line.startswith(prefix):
                parsed[key] = line[len(prefix) :].strip()
                current_key = "example" if key == "example" else None
                matched = True
                break
            if line.startswith("[line ") and prefix in line:
                parsed[key] = line.split(prefix, 1)[1].strip()
                current_key = "example" if key == "example" else None
                matched = True
                break
        if matched:
            continue
        if current_key == "example":
            existing = parsed.get("example", "")
            parsed["example"] = f"{existing}\n{raw_line}" if existing else raw_line
    return parsed or None


def _strip_traceback(text: str) -> str:
    if "Traceback" not in text:
        return text
    return text.split("Traceback", 1)[0].strip()


__all__ = ["build_error_pack"]
