from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.storage.factory import DEFAULT_DB_PATH, create_store
from namel3ss.runtime.storage.metadata import PersistenceMetadata


def run_persist(app_path: str, args: list[str]) -> int:
    if not Path(app_path).exists():
        raise Namel3ssError(f"App file '{app_path}' not found")
    if not args:
        raise Namel3ssError("Missing persist subcommand. Use: status|reset")
    cmd = args[0]
    tail = args[1:]
    if cmd == "status":
        return _status()
    if cmd == "reset":
        confirmed = "--yes" in tail
        return _reset(confirmed)
    raise Namel3ssError(f"Unknown persist subcommand '{cmd}'. Supported: status, reset")


def _status() -> int:
    store = create_store()
    meta = store.get_metadata()
    _print_status(meta)
    _close_store(store)
    return 0


def _reset(confirmed: bool) -> int:
    store = create_store()
    meta = store.get_metadata()
    if not meta.enabled or meta.kind != "sqlite":
        _print_disabled_message(meta)
        _close_store(store)
        return 0
    if not confirmed:
        path_hint = f" at {meta.path}" if meta.path else ""
        print(f"Persistence is enabled{path_hint}. Refusing to reset without --yes.")
        _close_store(store)
        return 1
    store.clear()
    print(f"Persisted store reset at {meta.path}")
    if meta.schema_version is not None:
        print(f"Schema version preserved: {meta.schema_version}")
    _close_store(store)
    return 0


def _print_status(meta: PersistenceMetadata) -> None:
    enabled = "true" if meta.enabled else "false"
    schema = meta.schema_version if meta.schema_version is not None else "n/a"
    path = meta.path or "none"
    print(f"Persistence enabled: {enabled}")
    print(f"Store kind: {meta.kind}")
    print(f"Path: {path}")
    print(f"Schema version: {schema}")
    if not meta.enabled:
        print(f"Guidance: set N3_PERSIST=1 to enable SQLite at {DEFAULT_DB_PATH}.")


def _print_disabled_message(meta: PersistenceMetadata) -> None:
    if meta.enabled:
        print("Persistence is enabled but not using SQLite. Nothing to reset.")
        return
    print("Persistence disabled (memory store). Nothing to reset.")
    print(f"Guidance: set N3_PERSIST=1 to enable SQLite at {DEFAULT_DB_PATH}.")


def _close_store(store) -> None:
    closer = getattr(store, "close", None)
    if callable(closer):
        try:
            closer()
        except Exception:
            pass
