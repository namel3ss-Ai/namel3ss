from __future__ import annotations

import os
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.server.lock.port_lock import (
    acquire_runtime_port_lock,
    read_runtime_port_lock,
    runtime_port_lock_path,
)


def test_runtime_port_lock_rejects_active_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n', encoding="utf-8")
    lock_path = runtime_port_lock_path(host="127.0.0.1", port=7399, lock_root=tmp_path)
    lock_path.write_text(
        '{"app_path":"existing/app.ai","command":"n3 run","host":"local","mode":"run","owner_pid":424242,"port":7399}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "namel3ss.runtime.server.lock.port_lock.recover_stale_port_lock",
        lambda *_args, **_kwargs: False,
    )
    with pytest.raises(Namel3ssError) as exc:
        acquire_runtime_port_lock(
            host="127.0.0.1",
            port=7399,
            app_path=app_path,
            mode="run",
            lock_root=tmp_path,
        )
    assert "Runtime already running" in str(exc.value)


def test_runtime_port_lock_recovers_stale_owner_file(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n', encoding="utf-8")
    lock_path = runtime_port_lock_path(host="127.0.0.1", port=7401, lock_root=tmp_path)
    lock_path.write_text(
        '{"app_path":"stale/app.ai","command":"n3 run","host":"local","mode":"run","owner_pid":-1,"port":7401}\n',
        encoding="utf-8",
    )
    lease = acquire_runtime_port_lock(
        host="127.0.0.1",
        port=7401,
        app_path=app_path,
        mode="run",
        lock_root=tmp_path,
    )
    payload = read_runtime_port_lock(lock_path)
    assert payload.get("owner_pid") == os.getpid()
    lease.release()
    assert not lock_path.exists()


def test_runtime_port_lock_release_uses_reference_count(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n', encoding="utf-8")
    lock_path = runtime_port_lock_path(host="127.0.0.1", port=7403, lock_root=tmp_path)
    first = acquire_runtime_port_lock(
        host="127.0.0.1",
        port=7403,
        app_path=app_path,
        mode="run",
        lock_root=tmp_path,
    )
    second = acquire_runtime_port_lock(
        host="127.0.0.1",
        port=7403,
        app_path=app_path,
        mode="run",
        lock_root=tmp_path,
    )
    assert lock_path.exists()
    first.release()
    assert lock_path.exists()
    second.release()
    assert not lock_path.exists()
