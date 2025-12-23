from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.storage.factory import DEFAULT_DB_PATH, create_store
from namel3ss.runtime.storage.metadata import PersistenceMetadata

DEFAULT_DB_PATH_POSIX = DEFAULT_DB_PATH.as_posix()


def run_data(app_path: str | None, args: list[str], *, alias: str = "data") -> int:
    resolved_path = _resolve_app_path(app_path)
    cmd = args[0] if args else "status"
    tail = args[1:] if args else []
    if cmd == "status":
        return _status(resolved_path.as_posix())
    if cmd == "reset":
        confirmed = "--yes" in tail
        return _reset(resolved_path.as_posix(), confirmed)
    raise Namel3ssError(f"Unknown {alias} subcommand '{cmd}'. Supported: status, reset")


def run_persist(app_path: str | None, args: list[str]) -> int:
    return run_data(app_path, args, alias="persist")


def _status(app_path: str) -> int:
    config = load_config(app_path=Path(app_path))
    if config.persistence.target == "edge":
        print("Persistence target: edge (not implemented).")
        print("Guidance: use sqlite for local dev or postgres for production.")
        return 1
    store = create_store(config=config)
    meta = store.get_metadata()
    _print_status(meta, config.persistence.target)
    _close_store(store)
    return 0


def _reset(app_path: str, confirmed: bool) -> int:
    config = load_config(app_path=Path(app_path))
    if config.persistence.target == "edge":
        print("Persistence target: edge (not implemented). Nothing to reset.")
        print("Guidance: use sqlite for local dev or postgres for production.")
        return 1
    store = create_store(config=config)
    meta = store.get_metadata()
    if not meta.enabled or meta.kind != "sqlite":
        _print_disabled_message(meta, config.persistence.target)
        _close_store(store)
        return 0
    if not confirmed and not _confirm_reset():
        path_hint = f" at {meta.path}" if meta.path else ""
        print(f"Persistence is enabled{path_hint}. Reset aborted.")
        _close_store(store)
        return 1
    store.clear()
    print(f"Persisted store reset at {meta.path}")
    if meta.schema_version is not None:
        print(f"Schema version preserved: {meta.schema_version}")
    _close_store(store)
    return 0


def _print_status(meta: PersistenceMetadata, target: str) -> None:
    enabled = "true" if meta.enabled else "false"
    schema = meta.schema_version if meta.schema_version is not None else "n/a"
    path_raw = meta.path or "none"
    path = Path(path_raw).as_posix() if path_raw not in {"none"} else path_raw
    print(f"Persistence enabled: {enabled}")
    print(f"Store kind: {meta.kind}")
    print(f"Target: {target}")
    print(f"Path: {path}")
    print(f"Schema version: {schema}")
    if not meta.enabled:
        print(f"Guidance: set N3_PERSIST_TARGET=sqlite to enable SQLite at {DEFAULT_DB_PATH_POSIX}.")


def _print_disabled_message(meta: PersistenceMetadata, target: str) -> None:
    if meta.enabled:
        print("Persistence is enabled but not using SQLite. Nothing to reset.")
        print(f"Target: {target}")
        return
    print("Persistence disabled (memory store). Nothing to reset.")
    print(f"Guidance: set N3_PERSIST_TARGET=sqlite to enable SQLite at {DEFAULT_DB_PATH_POSIX}.")


def _close_store(store) -> None:
    closer = getattr(store, "close", None)
    if callable(closer):
        try:
            closer()
        except Exception:
            pass


def _confirm_reset() -> bool:
    try:
        response = input("Type RESET to confirm: ")
    except EOFError:
        response = ""
    return response.strip() == "RESET"


def _resolve_app_path(app_path: str | None) -> Path:
    if app_path:
        path = Path(app_path)
        if not path.exists():
            raise Namel3ssError(f"App file '{app_path}' not found")
        return path.resolve()
    root = Path.cwd()
    ai_files = sorted(root.glob("*.ai"))
    app_file = root / "app.ai"
    if app_file.exists():
        if len(ai_files) > 1:
            sample = ", ".join(path.name for path in ai_files)
            raise Namel3ssError(
                build_guidance_message(
                    what="Multiple .ai files found in this directory.",
                    why=f"Found: {sample}.",
                    fix="Pass the app file path explicitly.",
                    example="n3 app.ai data",
                )
            )
        return app_file.resolve()
    if not ai_files:
        raise Namel3ssError(
            build_guidance_message(
                what="No .ai app file found in this directory.",
                why="`n3 data` runs from a project folder containing app.ai.",
                fix="Run inside the folder that contains app.ai or pass the file path explicitly.",
                example="n3 app.ai data",
            )
        )
    sample = ", ".join(path.name for path in ai_files)
    raise Namel3ssError(
        build_guidance_message(
            what="app.ai was not found in this directory.",
            why=f"Found other .ai files: {sample}.",
            fix="Pass the app file path explicitly.",
            example=f"n3 {ai_files[0].name} data",
        )
    )
