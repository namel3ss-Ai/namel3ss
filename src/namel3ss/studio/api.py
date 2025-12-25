from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.errors.payload import build_error_from_exception
from namel3ss.ir.nodes import lower_program
from namel3ss.lint.engine import lint_source
from namel3ss.parser.core import parse
from namel3ss.module_loader import load_project
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.runtime.preferences.factory import preference_store_for_app, app_pref_key
from namel3ss.studio.edit import apply_edit_to_source
from namel3ss.studio.session import SessionState
from namel3ss.studio.tool_wizard import run_tool_wizard
from namel3ss.cli.tools_support import build_bindings_plan
from namel3ss.runtime.tools.bindings import bindings_path, write_tool_bindings
from namel3ss.runtime.packs.ops import install_pack, verify_pack as verify_pack_install, enable_pack as enable_pack_install, disable_pack as disable_pack_install
from namel3ss.runtime.packs.registry import load_pack_registry, pack_payload
from namel3ss.runtime.packs.config import read_pack_config
from namel3ss.tools.health.analyze import analyze_tool_health
from namel3ss.ui.manifest import build_manifest
from namel3ss.version import get_version


def _load_program(source: str):
    ast_program = parse(source)
    return lower_program(ast_program)


def get_summary_payload(source: str, path: str) -> dict:
    try:
        program_ir = _load_program(source)
        counts = {
            "records": len(program_ir.records),
            "flows": len(program_ir.flows),
            "pages": len(program_ir.pages),
            "ais": len(program_ir.ais),
            "agents": len(program_ir.agents),
            "tools": len(program_ir.tools),
        }
        return {"ok": True, "file": path, "counts": counts}
    except Namel3ssError as err:
        return {"ok": False, "error": format_error(err, source)}


def get_ui_payload(source: str, session: SessionState | None = None, app_path: str | None = None) -> dict:
    try:
        session = session or SessionState()
        program_ir = _load_program(source)
        config = load_config(app_path=Path(app_path) if app_path else None)
        identity = resolve_identity(config, getattr(program_ir, "identity", None))
        preference_store = preference_store_for_app(app_path, getattr(program_ir, "theme_preference", {}).get("persist"))
        persisted, _ = preference_store.load_theme(app_pref_key(app_path))
        runtime_theme = session.runtime_theme or persisted or getattr(program_ir, "theme", "system")
        session.runtime_theme = runtime_theme
        manifest = build_manifest(
            program_ir,
            state=session.state,
            store=session.store,
            runtime_theme=runtime_theme,
            persisted_theme=persisted,
            identity=identity,
        )
        return manifest
    except Namel3ssError as err:
        return {"ok": False, "error": format_error(err, source)}


def get_actions_payload(source: str) -> dict:
    try:
        program_ir = _load_program(source)
        config = load_config()
        identity = resolve_identity(config, getattr(program_ir, "identity", None))
        manifest = build_manifest(program_ir, state={}, store=MemoryStore(), identity=identity)
        data = _actions_from_manifest(manifest)
        return {"ok": True, "count": len(data), "actions": data}
    except Namel3ssError as err:
        return {"ok": False, "error": format_error(err, source)}


def get_lint_payload(source: str) -> dict:
    findings = lint_source(source)
    return {
        "ok": len(findings) == 0,
        "count": len(findings),
        "findings": [f.to_dict() for f in findings],
    }


def get_tools_payload(source: str, app_path: str) -> dict:
    try:
        app_file = Path(app_path)
        project = load_project(app_file, source_overrides={app_file: source})
        report = analyze_tool_health(project)
        app_root = project.app_path.parent
        payload = _tool_inventory_payload(report, app_root)
        payload["ok"] = True
        return payload
    except Namel3ssError as err:
        return {"ok": False, "error": format_error(err, source)}


def get_packs_payload(app_path: str) -> dict:
    try:
        app_file = Path(app_path)
        app_root = app_file.parent
        config = read_pack_config(app_root)
        registry = load_pack_registry(app_root, _config_from_pack_config(config))
        payload = {
            "ok": True,
            "app_root": str(app_root),
            "packs": [pack_payload(pack) for pack in registry.packs.values()],
            "collisions": sorted(registry.collisions.keys()),
            "enabled_packs": config.enabled_packs,
            "disabled_packs": config.disabled_packs,
            "pinned_tools": config.pinned_tools,
        }
        return payload
    except Namel3ssError as err:
        return {"ok": False, "error": format_error(err, "")}


def apply_pack_add(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Body must be a JSON object"}
    source = payload.get("path")
    if not isinstance(source, str) or not source:
        return {"ok": False, "error": "path is required"}
    try:
        app_root = Path(app_path).parent
        pack_id = install_pack(app_root, Path(source))
        return {"ok": True, "pack_id": pack_id}
    except Namel3ssError as err:
        return {"ok": False, "error": str(err)}


def apply_pack_verify(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Body must be a JSON object"}
    pack_id = payload.get("pack_id")
    if not isinstance(pack_id, str) or not pack_id:
        return {"ok": False, "error": "pack_id is required"}
    try:
        app_root = Path(app_path).parent
        verify_pack_install(app_root, pack_id)
        return {"ok": True, "pack_id": pack_id}
    except Namel3ssError as err:
        return {"ok": False, "error": str(err)}


def apply_pack_enable(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Body must be a JSON object"}
    pack_id = payload.get("pack_id")
    if not isinstance(pack_id, str) or not pack_id:
        return {"ok": False, "error": "pack_id is required"}
    try:
        app_root = Path(app_path).parent
        enable_pack_install(app_root, pack_id)
        return {"ok": True, "pack_id": pack_id}
    except Namel3ssError as err:
        return {"ok": False, "error": str(err)}


def apply_pack_disable(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Body must be a JSON object"}
    pack_id = payload.get("pack_id")
    if not isinstance(pack_id, str) or not pack_id:
        return {"ok": False, "error": "pack_id is required"}
    try:
        app_root = Path(app_path).parent
        disable_pack_install(app_root, pack_id)
        return {"ok": True, "pack_id": pack_id}
    except Namel3ssError as err:
        return {"ok": False, "error": str(err)}


def _config_from_pack_config(config):
    from namel3ss.config.model import AppConfig, ToolPacksConfig

    app = AppConfig()
    app.tool_packs = ToolPacksConfig(
        enabled_packs=config.enabled_packs,
        disabled_packs=config.disabled_packs,
        pinned_tools=config.pinned_tools,
    )
    return app


def apply_tools_auto_bind(source: str, app_path: str) -> dict:
    try:
        app_file = Path(app_path)
        project = load_project(app_file, source_overrides={app_file: source})
        report = analyze_tool_health(project)
        if not report.bindings_valid:
            return {"ok": False, "error": report.bindings_error or "Bindings file is invalid."}
        app_root = project.app_path.parent
        plan = build_bindings_plan(app_root, project.program, report.bindings)
        stubs_written: list[str] = []
        stubs_skipped: list[str] = []
        for stub in plan.stubs:
            if stub.exists:
                stubs_skipped.append(str(stub.path))
                continue
            stub.path.parent.mkdir(parents=True, exist_ok=True)
            stub.path.write_text(stub.content, encoding="utf-8")
            stubs_written.append(str(stub.path))
        bindings_file = bindings_path(app_root)
        if plan.missing:
            bindings_file = write_tool_bindings(app_root, plan.proposed)
        return {
            "ok": True,
            "missing_bound": plan.missing,
            "bindings_path": str(bindings_file),
            "stubs_written": stubs_written,
            "stubs_skipped": stubs_skipped,
        }
    except Namel3ssError as err:
        return {"ok": False, "error": format_error(err, source)}


def get_version_payload() -> dict:
    return {"ok": True, "version": get_version()}


def execute_action(source: str, session: SessionState | None, action_id: str, payload: dict, app_path: str | None = None) -> dict:
    try:
        session = session or SessionState()
        program_ir = _load_program(source)
        config = load_config(app_path=Path(app_path) if app_path else None)
        response = handle_action(
            program_ir,
            action_id=action_id,
            payload=payload,
            state=session.state,
            store=session.store,
            runtime_theme=session.runtime_theme or getattr(program_ir, "theme", "system"),
            preference_store=preference_store_for_app(app_path, getattr(program_ir, "theme_preference", {}).get("persist")),
            preference_key=app_pref_key(app_path),
            allow_theme_override=getattr(program_ir, "theme_preference", {}).get("allow_override"),
            config=config,
        )
        if response and isinstance(response, dict):
            ui_theme = (response.get("ui") or {}).get("theme") if response.get("ui") else None
            if ui_theme and ui_theme.get("current"):
                session.runtime_theme = ui_theme.get("current")
        return response
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="engine", source=source)


def apply_edit(app_path: str, op: str, target: dict, value: str, session: SessionState) -> dict:
    source_text = Path(app_path).read_text(encoding="utf-8")
    formatted_source, program_ir, manifest = apply_edit_to_source(source_text, op, target, value, session)
    Path(app_path).write_text(formatted_source, encoding="utf-8")
    actions = _actions_from_manifest(manifest)
    lint_payload = get_lint_payload(formatted_source)
    summary = _summary_from_program(program_ir, app_path)
    return {
        "ok": True,
        "ui": manifest,
        "actions": {"ok": True, "count": len(actions), "actions": actions},
        "lint": lint_payload,
        "summary": summary,
    }


def apply_tool_wizard(app_path: str, payload: dict) -> dict:
    return run_tool_wizard(Path(app_path), payload)


def _tool_inventory_payload(report, app_root: Path) -> dict:
    packs = []
    for name in sorted(report.pack_tools):
        for provider in report.pack_tools[name]:
            packs.append(
                {
                    "name": name,
                    "pack_id": provider.pack_id,
                    "pack_name": provider.pack_name,
                    "pack_version": provider.pack_version,
                    "verified": provider.verified,
                    "enabled": provider.enabled,
                    "runner": provider.runner,
                    "source": provider.source,
                    "status": _status_for_pack(report, name, provider),
                }
            )
    declared = [
        {"name": tool.name, "kind": tool.kind, "status": _status_for_declared(report, tool.name)}
        for tool in sorted(report.declared_tools, key=lambda item: item.name)
    ]
    bindings = [
        {
            "name": name,
            "entry": binding.entry,
            "runner": binding.runner or "local",
            "status": _status_for_binding(report, name),
        }
        for name, binding in sorted(report.bindings.items())
    ]
    invalid = sorted(
        set(
            report.invalid_bindings
            + report.invalid_runners
            + report.service_missing_urls
            + report.container_missing_images
            + report.container_missing_runtime
        )
    )
    ok_count = len([tool for tool in declared if tool["kind"] == "python" and tool["status"] == "ok"])
    summary = {
        "ok": ok_count,
        "missing": len(report.missing_bindings),
        "unused": len(report.unused_bindings),
        "collisions": len(report.collisions) + len(report.pack_collisions),
        "invalid": len(invalid),
    }
    return {
        "app_root": str(app_root),
        "bindings_path": str(bindings_path(app_root)),
        "bindings_valid": report.bindings_valid,
        "bindings_error": report.bindings_error,
        "summary": summary,
        "packs": packs,
        "pack_collisions": report.pack_collisions,
        "pack_status": [pack.__dict__ for pack in report.packs],
        "declared": declared,
        "bindings": bindings,
        "missing_bindings": report.missing_bindings,
        "unused_bindings": report.unused_bindings,
        "collisions": report.collisions,
        "invalid_bindings": report.invalid_bindings,
        "invalid_runners": report.invalid_runners,
        "service_missing_urls": report.service_missing_urls,
        "container_missing_images": report.container_missing_images,
        "container_missing_runtime": report.container_missing_runtime,
        "issues": [issue.__dict__ for issue in report.issues],
    }


def _status_for_pack(report, name: str, provider) -> str:
    if name in report.pack_collisions:
        return "collision"
    if provider.source == "builtin_pack":
        return "ok"
    if not provider.verified:
        return "unverified"
    if not provider.enabled:
        return "disabled"
    return "ok"


def _status_for_declared(report, name: str) -> str:
    if name in report.collisions:
        return "collision"
    if name in report.missing_bindings:
        return "missing binding"
    return "ok"


def _status_for_binding(report, name: str) -> str:
    if name in report.collisions:
        return "collision"
    if name in report.invalid_bindings or name in report.invalid_runners:
        return "invalid binding"
    if name in report.service_missing_urls:
        return "invalid binding"
    if name in report.container_missing_images:
        return "invalid binding"
    if name in report.container_missing_runtime:
        return "invalid binding"
    if name in report.unused_bindings:
        return "unused binding"
    return "ok"


def _actions_from_manifest(manifest: dict) -> list[dict]:
    actions = manifest.get("actions", {})
    sorted_ids = sorted(actions.keys())
    data = []
    for action_id in sorted_ids:
        entry = actions[action_id]
        item = {"id": action_id, "type": entry.get("type")}
        if entry.get("type") == "call_flow":
            item["flow"] = entry.get("flow")
        if entry.get("type") == "submit_form":
            item["record"] = entry.get("record")
        data.append(item)
    return data


def _summary_from_program(program_ir, path: str) -> dict:
    counts = {
        "records": len(program_ir.records),
        "flows": len(program_ir.flows),
        "pages": len(program_ir.pages),
        "ais": len(program_ir.ais),
        "agents": len(program_ir.agents),
        "tools": len(program_ir.tools),
    }
    return {"ok": True, "file": path, "counts": counts}
