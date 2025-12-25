from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib import request

from namel3ss.runtime.capabilities.gates import (
    check_env_read,
    check_env_write,
    check_filesystem,
    check_network,
    check_secret_allowed,
    check_subprocess,
)
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext
from namel3ss.runtime.capabilities.secrets import normalize_secret_name


_context: CapabilityContext | None = None
_checks: list[dict[str, object]] = []


def configure(context: dict[str, object]) -> None:
    global _context
    _context = CapabilityContext.from_dict(context)
    clear_checks()


def clear_checks() -> None:
    _checks.clear()
    if _context:
        _context.allowed_emitted.clear()


def drain_checks() -> list[dict[str, object]]:
    output = list(_checks)
    _checks.clear()
    return output


def safe_open(path: str | Path, mode: str = "r", *, encoding: str | None = None, create_dirs: bool = False):
    if _context:
        check_filesystem(_context, _record_check, path=path, mode=mode)
    if create_dirs and _is_write_mode(mode):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return open(path, mode, encoding=encoding)


def safe_urlopen(req, *args, **kwargs):
    url, method = _url_and_method(req)
    if _context:
        check_network(_context, _record_check, url=url, method=method)
    return request.urlopen(req, *args, **kwargs)


def safe_env_get(key: str, default: str | None = None) -> str | None:
    if _context:
        check_env_read(_context, _record_check, key=key)
        secret_name = normalize_secret_name(key)
        if secret_name:
            check_secret_allowed(_context, _record_check, secret_name=secret_name)
    return os.getenv(key, default)


def safe_env_set(key: str, value: str) -> None:
    if _context:
        check_env_write(_context, _record_check, key=key)
        secret_name = normalize_secret_name(key)
        if secret_name:
            check_secret_allowed(_context, _record_check, secret_name=secret_name)
    os.environ[key] = value


def safe_run(argv: list[str], *args, **kwargs):
    if _context:
        check_subprocess(_context, _record_check, argv=list(argv))
    return subprocess.run(argv, *args, **kwargs)


def _record_check(check: CapabilityCheck) -> None:
    if _context is None:
        return
    if check.allowed and check.capability in _context.allowed_emitted:
        return
    if check.allowed:
        _context.allowed_emitted.add(check.capability)
    _checks.append(check.to_dict())


def _is_write_mode(mode: str) -> bool:
    return any(flag in mode for flag in ("w", "a", "x", "+"))


def _url_and_method(req) -> tuple[str, str]:
    if isinstance(req, request.Request):
        return req.full_url, req.get_method()
    return str(req), "GET"


__all__ = [
    "clear_checks",
    "configure",
    "drain_checks",
    "safe_env_get",
    "safe_env_set",
    "safe_open",
    "safe_run",
    "safe_urlopen",
]
