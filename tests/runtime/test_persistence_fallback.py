from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.memory_persist.writer import write_snapshot
from namel3ss.runtime.persistence_paths import resolve_persistence_root, resolve_writable_path
from namel3ss.runtime.storage.factory import create_store
from namel3ss.runtime.storage.sqlite_store import SQLiteStore


def _make_unwritable(path: Path) -> bool:
    path.chmod(stat.S_IRUSR | stat.S_IXUSR)
    return not os.access(path, os.W_OK)


def test_memory_persist_creates_directory(tmp_path: Path) -> None:
    manager = MemoryManager()
    snapshot_path = write_snapshot(manager, project_root=str(tmp_path), app_path=None)
    assert snapshot_path is not None
    assert snapshot_path.exists()
    assert snapshot_path.parent.is_dir()
    assert snapshot_path.parent.name == "memory"
    assert snapshot_path.parent.parent.name == ".namel3ss"


def test_memory_persist_falls_back_when_root_unwritable(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("chmod-based unwritable dir check is unreliable on Windows")
    root = tmp_path / "readonly"
    root.mkdir()
    if not _make_unwritable(root):
        pytest.skip("Unable to make directory unwritable")

    manager = MemoryManager()
    snapshot_path = write_snapshot(manager, project_root=str(root), app_path=None)

    assert snapshot_path is not None
    expected_root = resolve_persistence_root(root, None)
    assert expected_root is not None
    expected_dir = expected_root / ".namel3ss" / "memory"
    assert snapshot_path.parent == expected_dir
    assert snapshot_path.exists()
    assert not (root / ".namel3ss").exists()


def test_sqlite_falls_back_when_root_unwritable(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("chmod-based unwritable dir check is unreliable on Windows")
    root = tmp_path / "readonly_db"
    root.mkdir()
    if not _make_unwritable(root):
        pytest.skip("Unable to make directory unwritable")

    db_path = root / "data.db"
    config = AppConfig()
    config.persistence.target = "sqlite"
    config.persistence.db_path = str(db_path)

    store = create_store(config=config)
    try:
        assert isinstance(store, SQLiteStore)
        assert store.db_path == resolve_writable_path(db_path)
    finally:
        store.conn.close()


def test_persist_root_override_for_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    persist_root = tmp_path / "persist"
    monkeypatch.setenv("N3_PERSIST_ROOT", str(persist_root))
    manager = MemoryManager()
    snapshot_path = write_snapshot(manager, project_root=str(tmp_path / "project"), app_path=None)
    assert snapshot_path is not None
    assert snapshot_path.parent == persist_root / ".namel3ss" / "memory"
    assert snapshot_path.exists()


def test_persist_root_override_for_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    persist_root = tmp_path / "persist"
    monkeypatch.setenv("N3_PERSIST_ROOT", str(persist_root))
    config = AppConfig()
    config.persistence.target = "sqlite"
    config.persistence.db_path = ".namel3ss/data.db"

    store = create_store(config=config)
    try:
        assert isinstance(store, SQLiteStore)
        assert store.db_path == persist_root / ".namel3ss" / "data.db"
    finally:
        store.conn.close()
