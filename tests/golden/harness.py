from __future__ import annotations

import json
import os
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from namel3ss.cli.app_loader import load_program
from namel3ss.config.model import AppConfig
from namel3ss.determinism import canonicalize_run_payload, run_payload_hash, trace_hash
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.run_pipeline import build_flow_payload, finalize_run_payload
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.tools.bindings import write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from tests.spec_freeze.helpers.ir_dump import dump_ir

ROOT = Path(__file__).resolve().parent
APPS_DIR = ROOT / "apps"
SNAPSHOTS_DIR = ROOT / "snapshots"
MANIFEST_PATH = APPS_DIR / "manifest.json"


@dataclass(frozen=True)
class GoldenApp:
    app_id: str
    flow: str | None
    tags: list[str]
    state: dict[str, object]
    input: dict[str, object]
    identity: dict[str, object] | None
    parse_error: bool
    expect_ok: bool | None
    tool_bindings: dict[str, dict[str, object]]
    env_unset: list[str]


def load_manifest() -> list[GoldenApp]:
    payload = _read_json(MANIFEST_PATH)
    if not isinstance(payload, list):
        raise ValueError("golden manifest must be a list")
    apps: list[GoldenApp] = []
    seen: set[str] = set()
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("golden manifest entries must be objects")
        app_id = entry.get("id")
        if not isinstance(app_id, str) or not app_id:
            raise ValueError("golden manifest entries need an id")
        if app_id in seen:
            raise ValueError(f"duplicate golden app id: {app_id}")
        seen.add(app_id)
        flow = entry.get("flow")
        if flow is not None and not isinstance(flow, str):
            raise ValueError(f"flow must be a string for {app_id}")
        tags = entry.get("tags") or []
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError(f"tags must be a list of strings for {app_id}")
        state = entry.get("state") if isinstance(entry.get("state"), dict) else {}
        input_data = entry.get("input") if isinstance(entry.get("input"), dict) else {}
        identity = entry.get("identity") if isinstance(entry.get("identity"), dict) else None
        parse_error = bool(entry.get("parse_error"))
        expect_ok = entry.get("expect_ok")
        if expect_ok is not None and not isinstance(expect_ok, bool):
            raise ValueError(f"expect_ok must be bool for {app_id}")
        tool_bindings = entry.get("tool_bindings") if isinstance(entry.get("tool_bindings"), dict) else {}
        env_unset = entry.get("env_unset") or []
        if not isinstance(env_unset, list) or not all(isinstance(name, str) for name in env_unset):
            raise ValueError(f"env_unset must be a list of strings for {app_id}")
        apps.append(
            GoldenApp(
                app_id=app_id,
                flow=flow,
                tags=list(tags),
                state=dict(state),
                input=dict(input_data),
                identity=dict(identity) if identity is not None else None,
                parse_error=parse_error,
                expect_ok=expect_ok,
                tool_bindings=dict(tool_bindings),
                env_unset=list(env_unset),
            )
        )
    return sorted(apps, key=lambda app: app.app_id)


def run_golden_app(app: GoldenApp, workdir: Path) -> dict[str, object]:
    app_root = _prepare_app(app, workdir)
    app_file = app_root / "app.ai"
    source_text = app_file.read_text(encoding="utf-8")
    if app.tool_bindings:
        bindings = _build_bindings(app.tool_bindings)
        write_tool_bindings(app_root, bindings)
    with _unset_env(app.env_unset):
        if app.parse_error:
            return _run_parse_error(app, app_root, app_file, source_text)
        return _run_flow(app, app_root, app_file, source_text)


def write_snapshots(app_id: str, snapshot: dict[str, object], *, update: bool) -> None:
    paths = _snapshot_paths(app_id)
    _assert_snapshot(paths["ir"], snapshot["ir"], update=update)
    _assert_snapshot(paths["run"], snapshot["run"], update=update)
    _assert_snapshot(paths["traces"], snapshot["traces"], update=update)
    _assert_snapshot(paths["hashes"], snapshot["hashes"], update=update)


def _run_flow(app: GoldenApp, app_root: Path, app_file: Path, source_text: str) -> dict[str, object]:
    program, _sources = load_program(app_file.as_posix())
    if not app.flow:
        raise AssertionError(f"golden app {app.app_id} is missing flow")
    outcome = build_flow_payload(
        program,
        app.flow,
        state=app.state,
        input=app.input,
        store=MemoryStore(),
        memory_manager=None,
        runtime_theme=getattr(program, "theme", None),
        preference_store=None,
        preference_key=None,
        config=AppConfig(),
        identity=app.identity,
        source=source_text,
        project_root=app_root,
    )
    payload = finalize_run_payload(outcome.payload, secret_values=[])
    _assert_expect_ok(app, payload)
    ir_payload = dump_ir(program)
    return _snapshot_payload(ir_payload, payload)


def _run_parse_error(app: GoldenApp, app_root: Path, app_file: Path, source_text: str) -> dict[str, object]:
    try:
        load_program(app_file.as_posix())
    except Namel3ssError as err:
        error_payload = build_error_from_exception(err, kind="parse", source=source_text)
        error_payload = _normalize_error_payload(error_payload, app_file)
        payload = build_run_payload(
            ok=False,
            flow_name=None,
            state={},
            result=None,
            traces=[],
            project_root=app_root,
            error=err,
            error_payload=error_payload,
        )
        payload = finalize_run_payload(payload, secret_values=[])
        _assert_expect_ok(app, payload)
        ir_payload = {"parse_error": error_payload}
        return _snapshot_payload(ir_payload, payload)
    raise AssertionError(f"golden app {app.app_id} expected parse error")


def _snapshot_payload(ir_payload: dict, payload: dict) -> dict[str, object]:
    canonical_run = canonicalize_run_payload(payload)
    traces = canonical_run.get("traces", []) if isinstance(canonical_run, dict) else []
    raw_traces = payload.get("traces") if isinstance(payload.get("traces"), list) else []
    contract_hash = payload.get("contract", {}).get("trace_hash")
    computed = trace_hash(raw_traces)
    if isinstance(contract_hash, str) and contract_hash != computed:
        raise AssertionError("trace_hash mismatch between contract and recomputed value")
    hashes = {
        "trace_hash": computed,
        "run_payload_hash": run_payload_hash(payload),
        "contract_trace_hash": contract_hash,
    }
    return {
        "ir": ir_payload,
        "run": canonical_run,
        "traces": traces,
        "hashes": hashes,
    }


def _prepare_app(app: GoldenApp, workdir: Path) -> Path:
    if workdir.exists():
        shutil.rmtree(workdir)
    source_dir = APPS_DIR / app.app_id
    if not source_dir.exists():
        raise AssertionError(f"golden app folder missing: {source_dir}")
    shutil.copytree(source_dir, workdir)
    return workdir


def _build_bindings(raw: dict[str, dict[str, object]]) -> dict[str, ToolBinding]:
    bindings: dict[str, ToolBinding] = {}
    for name, entry in raw.items():
        if not isinstance(entry, dict):
            raise ValueError(f"tool binding for {name} must be an object")
        bindings[name] = ToolBinding(
            kind=_as_str(entry.get("kind")) or "",
            entry=_as_str(entry.get("entry")) or "",
            runner=_as_str(entry.get("runner")),
            url=_as_str(entry.get("url")),
            image=_as_str(entry.get("image")),
            command=_as_list(entry.get("command")),
            env=_as_env(entry.get("env")),
            purity=_as_str(entry.get("purity")),
            timeout_ms=_as_int(entry.get("timeout_ms")),
            sandbox=_as_bool(entry.get("sandbox")),
            enforcement=_as_str(entry.get("enforcement")),
        )
    return bindings


def _snapshot_paths(app_id: str) -> dict[str, Path]:
    base = SNAPSHOTS_DIR / app_id
    return {
        "ir": base / "ir.json",
        "run": base / "run.json",
        "traces": base / "traces.json",
        "hashes": base / "hashes.json",
    }


def _assert_snapshot(path: Path, payload: object, *, update: bool) -> None:
    if update:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return
    if not path.exists():
        raise AssertionError(f"missing snapshot {path}; set UPDATE_SNAPSHOTS=1")
    expected = _read_json(path)
    if payload != expected:
        raise AssertionError(f"snapshot mismatch for {path}")


def _assert_expect_ok(app: GoldenApp, payload: dict) -> None:
    if app.expect_ok is None:
        return
    actual = payload.get("ok") if isinstance(payload, dict) else None
    if actual is not app.expect_ok:
        raise AssertionError(f"golden app {app.app_id} expected ok={app.expect_ok} but got {actual}")


def _normalize_error_payload(payload: dict, app_file: Path) -> dict:
    if not isinstance(payload, dict):
        return {}
    normalized = dict(payload)
    details = payload.get("details")
    if isinstance(details, dict):
        details_copy = dict(details)
        file_value = details_copy.get("file")
        if isinstance(file_value, str) and file_value:
            details_copy["file"] = app_file.name
        normalized["details"] = details_copy
    return normalized


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


@contextmanager
def _unset_env(names: list[str]):
    if not names:
        yield
        return
    saved: dict[str, str | None] = {}
    for name in names:
        saved[name] = os.environ.pop(name, None)
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _as_list(value: object) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return None


def _as_env(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    if not all(isinstance(key, str) and isinstance(val, str) for key, val in value.items()):
        return None
    return dict(value)


def _as_int(value: object) -> int | None:
    return int(value) if isinstance(value, int) else None


def _as_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


__all__ = ["GoldenApp", "load_manifest", "run_golden_app", "write_snapshots"]
