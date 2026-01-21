from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.data.data_export import export_payload
from namel3ss.runtime.data.data_import import import_payload
from namel3ss.runtime.storage.factory import DEFAULT_DB_PATH, create_store
from namel3ss.runtime.storage.metadata import PersistenceMetadata

DEFAULT_DB_PATH_POSIX = DEFAULT_DB_PATH.as_posix()


def run_data(app_path: str | None, args: list[str], *, alias: str = "data") -> int:
    resolved_path = resolve_app_path(app_path)
    cmd = args[0] if args else "status"
    tail = args[1:] if args else []
    if cmd == "status":
        return _status(resolved_path.as_posix())
    if cmd == "reset":
        confirmed = "--yes" in tail
        return _reset(resolved_path.as_posix(), confirmed)
    if cmd == "export":
        return _export(resolved_path.as_posix(), tail)
    if cmd == "import":
        return _import(resolved_path.as_posix(), tail)
    raise Namel3ssError(f"Unknown {alias} subcommand '{cmd}'. Supported: status, reset, export, import")


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
        print("Persistence target: edge not implemented. Nothing to reset.")
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


@dataclass(frozen=True)
class _ExportParams:
    output_path: str | None
    json_mode: bool


@dataclass(frozen=True)
class _ImportParams:
    input_path: str
    json_mode: bool


def _export(app_path: str, args: list[str]) -> int:
    params = _parse_export_args(args)
    program, _sources = load_program(app_path)
    config = load_config(app_path=Path(app_path))
    store = create_store(config=config)
    try:
        payload = export_payload(
            program,
            store,
            config,
            project_root=Path(app_path).parent,
            app_path=app_path,
            destination=params.output_path,
        )
    finally:
        _close_store(store)
    if params.output_path:
        path = Path(params.output_path)
        path.write_text(
            canonical_json_dumps(payload, pretty=True, drop_run_keys=False),
            encoding="utf-8",
        )
        if params.json_mode:
            _print_json(payload)
        else:
            print(f"Exported data: {_describe_path(path, Path(app_path).parent)}")
        return 0
    _print_json(payload)
    return 0


def _import(app_path: str, args: list[str]) -> int:
    params = _parse_import_args(args)
    path = Path(params.input_path)
    if not path.exists():
        raise Namel3ssError(_missing_import_file_message(params.input_path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(_invalid_import_message(params.input_path, err)) from err
    program, _sources = load_program(app_path)
    config = load_config(app_path=Path(app_path))
    store = create_store(config=config)
    try:
        payload = import_payload(
            program,
            store,
            config,
            data,
            project_root=Path(app_path).parent,
            app_path=app_path,
        )
    finally:
        _close_store(store)
    if params.json_mode:
        _print_json(payload)
    else:
        _print_import_summary(payload, params.input_path, project_root=Path(app_path).parent)
    return 0 if payload.get("ok", True) else 1


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
    print("Persistence disabled in memory store. Nothing to reset.")
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


def _describe_path(path: Path, project_root: Path) -> str:
    try:
        resolved = path.resolve()
    except Exception:
        return path.as_posix()
    if resolved.is_absolute():
        try:
            return resolved.relative_to(project_root.resolve()).as_posix()
        except Exception:
            return resolved.name
    return resolved.as_posix()


def _print_json(payload: dict) -> None:
    print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))


def _print_import_summary(payload: dict, source: str, *, project_root: Path) -> None:
    ok = payload.get("ok", True)
    status = "ok" if ok else "errors"
    print(f"Imported data: {_describe_path(Path(source), project_root)}")
    print(f"Status: {status}")
    errors = payload.get("errors") if isinstance(payload.get("errors"), list) else []
    if errors:
        print(f"Errors: {len(errors)}")


def _parse_export_args(args: list[str]) -> _ExportParams:
    output_path = None
    json_mode = False
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg == "--out":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value("--out"))
            output_path = args[idx + 1]
            idx += 2
            continue
        if arg.startswith("-"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if output_path is None:
            output_path = arg
            idx += 1
            continue
        raise Namel3ssError(_too_many_args_message("export"))
    return _ExportParams(output_path=output_path, json_mode=json_mode)


def _parse_import_args(args: list[str]) -> _ImportParams:
    input_path = None
    json_mode = False
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg == "--in":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value("--in"))
            input_path = args[idx + 1]
            idx += 2
            continue
        if arg.startswith("-"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if input_path is None:
            input_path = arg
            idx += 1
            continue
        raise Namel3ssError(_too_many_args_message("import"))
    if not input_path:
        raise Namel3ssError(_missing_import_path_message())
    return _ImportParams(input_path=input_path, json_mode=json_mode)


def _missing_flag_value(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} flag is missing a value.",
        why="Data export/import requires a file path.",
        fix=f"Provide a path after {flag}.",
        example=f"n3 data export --out data.json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="Supported flags: --json, --out, --in.",
        fix="Remove the unsupported flag.",
        example="n3 data export --json",
    )


def _too_many_args_message(command: str) -> str:
    return build_guidance_message(
        what=f"Too many arguments for data {command}.",
        why=f"data {command} accepts a single path plus flags.",
        fix="Remove extra positional arguments.",
        example=f"n3 data {command} data.json",
    )


def _missing_import_path_message() -> str:
    return build_guidance_message(
        what="Import file path is missing.",
        why="Data import needs a JSON file.",
        fix="Provide the path to the export JSON file.",
        example="n3 data import data.json",
    )


def _missing_import_file_message(path: str) -> str:
    return build_guidance_message(
        what=f"Import file not found: {path}.",
        why="The path does not exist.",
        fix="Check the file name and try again.",
        example="n3 data import data.json",
    )


def _invalid_import_message(path: str, err: json.JSONDecodeError) -> str:
    where = f" at line {err.lineno}, column {err.colno}" if err.lineno and err.colno else ""
    return build_guidance_message(
        what=f"Import file is not valid JSON: {path}.",
        why=f"JSON parsing failed{where}: {err.msg}.",
        fix="Ensure the export file is valid JSON.",
        example="n3 data import data.json",
    )
