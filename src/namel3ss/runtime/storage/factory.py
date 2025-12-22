from __future__ import annotations

import os
from pathlib import Path

from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.storage.sqlite_store import SQLiteStore


DEFAULT_DB_PATH = Path(".namel3ss/data.db")


def _persist_enabled() -> bool:
    value = os.getenv("N3_PERSIST", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def create_store(db_path: Path | None = None):
    if not _persist_enabled():
        return MemoryStore()
    path = db_path or DEFAULT_DB_PATH
    return SQLiteStore(path)


def resolve_store(store=None):
    return store if store is not None else create_store()
