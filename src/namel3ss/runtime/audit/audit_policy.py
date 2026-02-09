from __future__ import annotations

import os
from typing import Mapping

from namel3ss.config.model import AppConfig


AUDIT_MODE_REQUIRED = "required"
AUDIT_MODE_OPTIONAL = "optional"
AUDIT_MODE_FORBIDDEN = "forbidden"
DEFAULT_AUDIT_MODE = AUDIT_MODE_OPTIONAL

_VALID_AUDIT_MODES = {
    AUDIT_MODE_REQUIRED,
    AUDIT_MODE_OPTIONAL,
    AUDIT_MODE_FORBIDDEN,
}


def resolve_audit_mode(config: AppConfig | None, *, env: Mapping[str, str] | None = None) -> str:
    env_map = env if isinstance(env, Mapping) else os.environ
    env_mode = _normalize_mode(env_map.get("N3_AUDIT_POLICY"))
    if env_mode:
        return env_mode
    config_mode = _normalize_mode(_read_config_mode(config))
    if config_mode:
        return config_mode
    return DEFAULT_AUDIT_MODE


def audit_writing_enabled(mode: str) -> bool:
    return mode in {AUDIT_MODE_REQUIRED, AUDIT_MODE_OPTIONAL}


def audit_writing_required(mode: str) -> bool:
    return mode == AUDIT_MODE_REQUIRED


def build_audit_policy_status(
    mode: str,
    *,
    attempted: bool,
    written: bool,
    error: str | None = None,
) -> dict[str, object]:
    normalized_mode = _normalize_mode(mode) or DEFAULT_AUDIT_MODE
    payload = {
        "mode": normalized_mode,
        "required": normalized_mode == AUDIT_MODE_REQUIRED,
        "forbidden": normalized_mode == AUDIT_MODE_FORBIDDEN,
        "attempted": bool(attempted),
        "written": bool(written),
    }
    error_text = str(error or "").strip()
    if error_text:
        payload["error"] = error_text
    return payload


def _read_config_mode(config: AppConfig | None) -> object:
    if config is None:
        return None
    audit = getattr(config, "audit", None)
    if audit is not None and hasattr(audit, "mode"):
        return getattr(audit, "mode")
    return getattr(config, "audit_policy", None)


def _normalize_mode(value: object) -> str:
    if not isinstance(value, str):
        return ""
    mode = value.strip().lower()
    if mode in _VALID_AUDIT_MODES:
        return mode
    return ""


__all__ = [
    "AUDIT_MODE_FORBIDDEN",
    "AUDIT_MODE_OPTIONAL",
    "AUDIT_MODE_REQUIRED",
    "DEFAULT_AUDIT_MODE",
    "audit_writing_enabled",
    "audit_writing_required",
    "build_audit_policy_status",
    "resolve_audit_mode",
]
