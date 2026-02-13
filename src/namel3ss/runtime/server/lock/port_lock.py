from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
import tempfile
import threading

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.server.lock.stale_lock_recovery import (
    is_process_running,
    recover_stale_port_lock,
)


_LOCK_MUTEX = threading.RLock()
_LOCK_COUNTS: dict[str, int] = {}
_LOCK_PATHS: dict[str, Path] = {}


@dataclass(frozen=True)
class RuntimePortLease:
    key: str
    host: str
    port: int
    owner_pid: int
    lock_path: Path | None
    active: bool

    def release(self) -> None:
        release_runtime_port_lock(self)


def acquire_runtime_port_lock(
    *,
    host: str,
    port: int,
    app_path: Path,
    mode: str,
    command: str | None = None,
    lock_root: Path | None = None,
    allow_reentrant: bool = True,
) -> RuntimePortLease:
    normalized_host = _normalize_host(host)
    normalized_port = int(port)
    owner_pid = int(os.getpid())
    key = lock_key(host=normalized_host, port=normalized_port)
    if normalized_port <= 0:
        return RuntimePortLease(
            key=key,
            host=normalized_host,
            port=normalized_port,
            owner_pid=owner_pid,
            lock_path=None,
            active=False,
        )

    with _LOCK_MUTEX:
        existing_count = _LOCK_COUNTS.get(key, 0)
        if existing_count > 0:
            if not allow_reentrant:
                path = _LOCK_PATHS.get(key)
                owner = read_runtime_port_lock(path) if path is not None else {}
                owner_pid = _int(owner.get("owner_pid"), default=int(os.getpid()))
                raise _runtime_lock_conflict_error(
                    host=normalized_host,
                    port=normalized_port,
                    owner_pid=owner_pid,
                    command=str(owner.get("command") or "").strip(),
                    app_path=Path(app_path).resolve(),
                )
            _LOCK_COUNTS[key] = existing_count + 1
            return RuntimePortLease(
                key=key,
                host=normalized_host,
                port=normalized_port,
                owner_pid=owner_pid,
                lock_path=_LOCK_PATHS.get(key),
                active=True,
            )

    path = runtime_port_lock_path(host=normalized_host, port=normalized_port, lock_root=lock_root)
    payload = _lock_payload(
        host=normalized_host,
        port=normalized_port,
        app_path=Path(app_path).resolve(),
        mode=mode,
        owner_pid=owner_pid,
        command=command,
    )
    for _ in range(0, 2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            owner = read_runtime_port_lock(path)
            owner_pid = _int(owner.get("owner_pid"), default=-1)
            if owner_pid == os.getpid():
                if not allow_reentrant:
                    raise _runtime_lock_conflict_error(
                        host=normalized_host,
                        port=normalized_port,
                        owner_pid=owner_pid,
                        command=str(owner.get("command") or "").strip(),
                        app_path=Path(app_path).resolve(),
                    )
                with _LOCK_MUTEX:
                    _LOCK_COUNTS[key] = _LOCK_COUNTS.get(key, 0) + 1
                    _LOCK_PATHS[key] = path
                return RuntimePortLease(
                    key=key,
                    host=normalized_host,
                    port=normalized_port,
                    owner_pid=int(os.getpid()),
                    lock_path=path,
                    active=True,
                )
            if recover_stale_port_lock(path, owner_pid=owner_pid):
                continue
            raise _runtime_lock_conflict_error(
                host=normalized_host,
                port=normalized_port,
                owner_pid=owner_pid,
                command=str(owner.get("command") or "").strip(),
                app_path=Path(app_path).resolve(),
            )
        else:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
                handle.write("\n")
            with _LOCK_MUTEX:
                _LOCK_COUNTS[key] = 1
                _LOCK_PATHS[key] = path
            return RuntimePortLease(
                key=key,
                host=normalized_host,
                port=normalized_port,
                owner_pid=int(os.getpid()),
                lock_path=path,
                active=True,
            )
    raise _runtime_lock_conflict_error(
        host=normalized_host,
        port=normalized_port,
        owner_pid=-1,
        command="",
        app_path=Path(app_path).resolve(),
    )


def release_runtime_port_lock(lease: RuntimePortLease | None) -> None:
    if lease is None or not lease.active:
        return
    key = lease.key
    path = lease.lock_path
    should_remove = False
    with _LOCK_MUTEX:
        count = _LOCK_COUNTS.get(key, 0)
        if count <= 1:
            _LOCK_COUNTS.pop(key, None)
            _LOCK_PATHS.pop(key, None)
            should_remove = True
        else:
            _LOCK_COUNTS[key] = count - 1
    if not should_remove or path is None:
        return
    owner = read_runtime_port_lock(path)
    owner_pid = _int(owner.get("owner_pid"), default=-1)
    if owner_pid > 0 and owner_pid != lease.owner_pid and is_process_running(owner_pid):
        return
    try:
        path.unlink()
    except FileNotFoundError:
        return


def runtime_port_lock_path(*, host: str, port: int, lock_root: Path | None = None) -> Path:
    root = lock_root or _default_lock_root()
    root.mkdir(parents=True, exist_ok=True)
    normalized_host = _normalize_host(host)
    safe_host = "".join(char if char.isalnum() else "_" for char in normalized_host) or "local"
    return root / f"runtime_port_{safe_host}_{int(port)}.lock.json"


def read_runtime_port_lock(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def lock_key(*, host: str, port: int) -> str:
    return f"{_normalize_host(host)}:{int(port)}"


def _default_lock_root() -> Path:
    custom_root = os.getenv("N3_RUNTIME_LOCK_DIR", "").strip()
    if custom_root:
        return Path(custom_root).expanduser().resolve()
    return Path(tempfile.gettempdir()) / "namel3ss_runtime_locks"


def _normalize_host(value: str) -> str:
    token = str(value or "").strip().lower()
    if token in {"", "127.0.0.1", "0.0.0.0", "localhost", "::1"}:
        return "local"
    return token


def _lock_payload(
    *,
    host: str,
    port: int,
    app_path: Path,
    mode: str,
    owner_pid: int,
    command: str | None,
) -> dict[str, object]:
    argv_text = " ".join(str(entry).strip() for entry in sys.argv if str(entry).strip())
    command_text = str(command or argv_text or "n3").strip()
    return {
        "app_path": app_path.as_posix(),
        "command": command_text,
        "host": host,
        "mode": str(mode or "").strip(),
        "owner_pid": int(owner_pid),
        "port": int(port),
    }


def _int(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except Exception:
        return default


def _runtime_lock_conflict_error(
    *,
    host: str,
    port: int,
    owner_pid: int,
    command: str,
    app_path: Path,
) -> Namel3ssError:
    owner_text = str(owner_pid) if owner_pid > 0 else "unknown"
    command_text = command or "unknown"
    return Namel3ssError(
        build_guidance_message(
            what=f"Runtime already running on {host}:{int(port)}.",
            why=f"Active lock owner pid={owner_text} command='{command_text}'.",
            fix="Stop the running process or choose another port.",
            example=f"n3 run {app_path.as_posix()} --port {int(port) + 1}",
        )
    )


__all__ = [
    "RuntimePortLease",
    "acquire_runtime_port_lock",
    "lock_key",
    "read_runtime_port_lock",
    "release_runtime_port_lock",
    "runtime_port_lock_path",
]
