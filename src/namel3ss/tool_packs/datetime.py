from __future__ import annotations

from datetime import datetime, timedelta, timezone


def now(payload: dict) -> dict:
    tz = _read_timezone(payload)
    current = datetime.now(tz)
    return {"iso": current.isoformat()}


def parse(payload: dict) -> dict:
    text = _require_text(payload, "text")
    fmt = payload.get("format")
    if fmt is None:
        parsed = datetime.fromisoformat(text)
    else:
        if not isinstance(fmt, str):
            raise ValueError("payload.format must be a string")
        parsed = datetime.strptime(text, fmt)
    return {"iso": parsed.isoformat()}


def format(payload: dict) -> dict:
    iso = _require_text(payload, "iso")
    fmt = _require_text(payload, "format")
    parsed = datetime.fromisoformat(iso)
    return {"text": parsed.strftime(fmt)}


def add_days(payload: dict) -> dict:
    iso = _require_text(payload, "iso")
    days = payload.get("days")
    if isinstance(days, bool) or not isinstance(days, (int, float)):
        raise ValueError("payload.days must be a number")
    parsed = datetime.fromisoformat(iso)
    updated = parsed + timedelta(days=float(days))
    return {"iso": updated.isoformat()}


def _read_timezone(payload: dict) -> timezone:
    value = payload.get("timezone", "utc")
    if value is None:
        return timezone.utc
    if not isinstance(value, str):
        raise ValueError("payload.timezone must be a string")
    name = value.strip().lower()
    if name in {"utc", "z"}:
        return timezone.utc
    if name in {"local", "system"}:
        return datetime.now().astimezone().tzinfo or timezone.utc
    raise ValueError("payload.timezone must be 'utc' or 'local'")


def _require_text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"payload.{key} must be a non-empty string")
    return value.strip()


__all__ = ["add_days", "format", "now", "parse"]
