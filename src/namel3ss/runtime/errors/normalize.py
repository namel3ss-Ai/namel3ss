from __future__ import annotations

from collections.abc import Mapping, Sequence

from namel3ss.runtime.errors.classification import (
    build_runtime_error,
    classify_runtime_error,
    is_runtime_error_category,
)


def normalize_runtime_error(value: object) -> dict[str, str] | None:
    if not isinstance(value, Mapping):
        return None
    category = value.get("category")
    if not is_runtime_error_category(category):
        return None
    return build_runtime_error(
        str(category),
        message=_text_value(value.get("message")),
        hint=_text_value(value.get("hint")),
        origin=_text_value(value.get("origin")),
        stable_code=_text_value(value.get("stable_code")),
    )


def attach_runtime_error_payload(
    payload: dict,
    *,
    status_code: int | None = None,
    endpoint: str | None = None,
    diagnostics: Sequence[Mapping[str, object] | dict[str, str]] | None = None,
) -> dict:
    if not isinstance(payload, dict):
        return payload
    primary = _resolve_primary_error(payload, status_code=status_code, endpoint=endpoint)
    secondary = _normalize_diagnostics(diagnostics)
    ordered = _ordered_errors(primary, secondary)
    if not ordered:
        payload.pop("runtime_error", None)
        payload.pop("runtime_errors", None)
        return payload
    payload["runtime_error"] = ordered[0]
    payload["runtime_errors"] = ordered
    if payload.get("ok") is True and primary is None:
        payload["degraded"] = True
    return payload


def merge_runtime_errors(
    *groups: Sequence[Mapping[str, object] | dict[str, str]] | None,
) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for group in groups:
        for item in _normalize_diagnostics(group):
            stable_code = item.get("stable_code")
            if stable_code in seen:
                continue
            seen.add(stable_code)
            merged.append(item)
    return merged


def _resolve_primary_error(
    payload: Mapping[str, object],
    *,
    status_code: int | None,
    endpoint: str | None,
) -> dict[str, str] | None:
    existing = normalize_runtime_error(payload.get("runtime_error"))
    if existing is not None:
        return existing
    if not _has_error_signal(payload, status_code=status_code):
        return None
    message, kind, details = _extract_error_context(payload)
    return classify_runtime_error(
        message=message,
        kind=kind,
        details=details,
        status_code=status_code,
        endpoint=endpoint,
        payload=payload,
    )


def _has_error_signal(payload: Mapping[str, object], *, status_code: int | None) -> bool:
    if status_code is not None and status_code >= 400:
        return True
    ok = payload.get("ok")
    if isinstance(ok, bool) and ok is False:
        return True
    if payload.get("error"):
        return True
    if payload.get("errors"):
        return True
    return False


def _extract_error_context(payload: Mapping[str, object]) -> tuple[str | None, str | None, Mapping[str, object] | None]:
    error = payload.get("error")
    kind = _text_value(payload.get("kind"))
    details = payload.get("details") if isinstance(payload.get("details"), Mapping) else None
    message = _text_value(payload.get("message"))

    if isinstance(error, Mapping):
        if not message:
            for key in ("message", "error", "why"):
                message = _text_value(error.get(key))
                if message:
                    break
        if not kind:
            kind = _text_value(error.get("kind"))
        if details is None and isinstance(error.get("details"), Mapping):
            details = error.get("details")  # type: ignore[assignment]
    elif isinstance(error, str) and not message:
        message = error

    if details is None and isinstance(payload.get("error_entry"), Mapping):
        details = payload.get("error_entry")  # type: ignore[assignment]
    return message, kind, details


def _normalize_diagnostics(
    diagnostics: Sequence[Mapping[str, object] | dict[str, str]] | None,
) -> list[dict[str, str]]:
    if not diagnostics:
        return []
    normalized: list[dict[str, str]] = []
    for item in diagnostics:
        entry = normalize_runtime_error(item)
        if entry is None:
            continue
        normalized.append(entry)
    return normalized


def _ordered_errors(
    primary: dict[str, str] | None,
    diagnostics: list[dict[str, str]],
) -> list[dict[str, str]]:
    ordered: list[dict[str, str]] = []
    seen: set[str] = set()

    def _append(entry: dict[str, str]) -> None:
        stable_code = entry.get("stable_code")
        if stable_code in seen:
            return
        seen.add(stable_code)
        ordered.append(entry)

    if primary is not None:
        _append(primary)
    for diagnostic in diagnostics:
        _append(diagnostic)
    return ordered


def _text_value(value: object) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


__all__ = [
    "attach_runtime_error_payload",
    "merge_runtime_errors",
    "normalize_runtime_error",
]
