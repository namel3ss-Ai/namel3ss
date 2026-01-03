from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.secrets import collect_secret_values, redact_payload, redact_text


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


@dataclass(frozen=True)
class SecurityWall:
    traces: list[dict]
    secret_values: list[str]
    capability_ctx: CapabilityContext


_ACTIVE_WALL: SecurityWall | None = None


def build_security_wall(config: AppConfig | None, traces: list[dict]) -> SecurityWall:
    from namel3ss.runtime.capabilities.model import CapabilityContext, EffectiveGuarantees, GUARANTEE_FIELDS

    secret_values = collect_secret_values(config)
    sources = {field: "engine" for field in GUARANTEE_FIELDS}
    sources["secrets_allowed"] = "engine"
    guarantees = EffectiveGuarantees(sources=sources)
    capability_ctx = CapabilityContext(
        tool_name="engine",
        resolved_source="engine",
        runner="engine",
        protocol_version=1,
        guarantees=guarantees,
    )
    return SecurityWall(traces=traces, secret_values=secret_values, capability_ctx=capability_ctx)


@contextmanager
def activate_security_wall(wall: SecurityWall):
    global _ACTIVE_WALL
    previous = _ACTIVE_WALL
    _ACTIVE_WALL = wall
    try:
        yield
    finally:
        _ACTIVE_WALL = previous


def redact_sensitive_payload(payload: object, secret_values: Iterable[str]) -> object:
    redacted = redact_payload(payload, secret_values)
    return _redact_sensitive_keys(redacted)


def resolve_secret_values(
    secret_values: Iterable[str] | None = None,
    *,
    config: AppConfig | None = None,
) -> list[str]:
    if secret_values is None:
        return collect_secret_values(config)
    return list(secret_values)


def read_env(key: str, default: str | None = None) -> str | None:
    guard_env_read(key)
    return os.getenv(key, default)


def guard_network(url: str, method: str) -> None:
    wall = _ACTIVE_WALL
    if wall is None:
        return
    record = _record_for(wall)
    try:
        from namel3ss.runtime.capabilities.gates import check_network
        from namel3ss.runtime.capabilities.gates.base import CapabilityViolation

        check_network(wall.capability_ctx, record, url=url, method=method)
    except CapabilityViolation as err:
        raise Namel3ssError(str(err)) from err


def guard_filesystem(path: str, mode: str) -> None:
    wall = _ACTIVE_WALL
    if wall is None:
        return
    record = _record_for(wall)
    try:
        from namel3ss.runtime.capabilities.gates import check_filesystem
        from namel3ss.runtime.capabilities.gates.base import CapabilityViolation

        check_filesystem(wall.capability_ctx, record, path=path, mode=mode)
    except CapabilityViolation as err:
        raise Namel3ssError(str(err)) from err


def guard_env_read(key: str) -> None:
    wall = _ACTIVE_WALL
    if wall is None:
        return
    record = _record_for(wall)
    try:
        from namel3ss.runtime.capabilities.gates import check_env_read, check_secret_allowed
        from namel3ss.runtime.capabilities.gates.base import CapabilityViolation
        from namel3ss.runtime.capabilities.secrets import normalize_secret_name

        check_env_read(wall.capability_ctx, record, key=key)
        secret_name = normalize_secret_name(key)
        if secret_name:
            check_secret_allowed(wall.capability_ctx, record, secret_name=secret_name)
    except CapabilityViolation as err:
        raise Namel3ssError(str(err)) from err


def guard_env_write(key: str) -> None:
    wall = _ACTIVE_WALL
    if wall is None:
        return
    record = _record_for(wall)
    try:
        from namel3ss.runtime.capabilities.gates import check_env_write, check_secret_allowed
        from namel3ss.runtime.capabilities.gates.base import CapabilityViolation
        from namel3ss.runtime.capabilities.secrets import normalize_secret_name

        check_env_write(wall.capability_ctx, record, key=key)
        secret_name = normalize_secret_name(key)
        if secret_name:
            check_secret_allowed(wall.capability_ctx, record, secret_name=secret_name)
    except CapabilityViolation as err:
        raise Namel3ssError(str(err)) from err


def guard_subprocess(argv: list[str]) -> None:
    wall = _ACTIVE_WALL
    if wall is None:
        return
    record = _record_for(wall)
    try:
        from namel3ss.runtime.capabilities.gates import check_subprocess
        from namel3ss.runtime.capabilities.gates.base import CapabilityViolation

        check_subprocess(wall.capability_ctx, record, argv=argv)
    except CapabilityViolation as err:
        raise Namel3ssError(str(err)) from err


def _record_for(wall: SecurityWall):
    from namel3ss.runtime.capabilities.gates.trace import record_capability_check

    return lambda check: record_capability_check(wall.capability_ctx, _coerce_check(check), wall.traces)


def _coerce_check(check: CapabilityCheck | dict) -> CapabilityCheck:
    from namel3ss.runtime.capabilities.model import CapabilityCheck

    if isinstance(check, CapabilityCheck):
        return check
    capability = check.get("capability")
    allowed = check.get("allowed")
    guarantee_source = check.get("guarantee_source")
    reason = check.get("reason")
    duration_ms = check.get("duration_ms")
    duration_val = int(duration_ms) if isinstance(duration_ms, int) else None
    return CapabilityCheck(
        capability=str(capability),
        allowed=bool(allowed),
        guarantee_source=str(guarantee_source),
        reason=str(reason),
        duration_ms=duration_val,
    )


def _redact_sensitive_keys(value: object) -> object:
    if isinstance(value, dict):
        redacted: dict[object, object] = {}
        for key, val in value.items():
            if _is_sensitive_key(key):
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = _redact_sensitive_keys(val)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive_keys(item) for item in value]
    if isinstance(value, str):
        return redact_text(value, [])
    return value


def _is_sensitive_key(key: object) -> bool:
    text = str(key).lower()
    return any(marker in text for marker in _SENSITIVE_KEY_MARKERS)


__all__ = [
    "SecurityWall",
    "activate_security_wall",
    "build_security_wall",
    "guard_env_read",
    "guard_env_write",
    "guard_filesystem",
    "guard_network",
    "guard_subprocess",
    "read_env",
    "redact_sensitive_payload",
    "resolve_secret_values",
]
