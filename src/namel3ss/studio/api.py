from __future__ import annotations

from pathlib import Path

from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.targets import parse_target
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.ir.nodes import lower_program
from namel3ss.lint.engine import lint_source
from namel3ss.parser.core import parse
from namel3ss.module_loader import load_project
from namel3ss.secrets import collect_secret_values, discover_required_secrets
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.runtime.preferences.factory import preference_store_for_app, app_pref_key
from namel3ss.studio.session import SessionState
from namel3ss.studio.diagnostics import collect_ai_context_diagnostics
from namel3ss.studio.trace_adapter import normalize_action_response
from namel3ss.runtime.tools.bindings import bindings_path
from namel3ss.tools.health.analyze import analyze_tool_health
from namel3ss.ui.manifest import build_manifest
from namel3ss.version import get_version
from namel3ss.graduation.matrix import build_capability_matrix
from namel3ss.graduation.render import render_graduation_lines, render_matrix_lines, render_summary_lines
from namel3ss.graduation.rules import evaluate_graduation
from namel3ss.studio.agent_builder import (
    apply_agent_wizard,
    get_agents_payload,
    run_agent_payload,
    run_handoff_action,
    update_memory_packs,
)
from namel3ss.validation import ValidationMode, ValidationWarning


def _load_program(source: str):
    ast_program = parse(source)
    return lower_program(ast_program)


def _load_project_program(source: str, path: str):
    app_file = Path(path)
    project = load_project(app_file, source_overrides={app_file: source})
    return project.program


def get_summary_payload(source: str, path: str) -> dict:
    try:
        program_ir = _load_project_program(source, path)
        file_value = Path(path).as_posix() if path else ""
        ai_providers = sorted(
            {
                (ai.provider or "").lower()
                for ai in program_ir.ais.values()
                if getattr(ai, "provider", None)
            }
        )
        counts = {
            "records": len(program_ir.records),
            "flows": len(program_ir.flows),
            "pages": len(program_ir.pages),
            "ais": len(program_ir.ais),
            "agents": len(program_ir.agents),
            "tools": len(program_ir.tools),
        }
        payload = {"ok": True, "file": file_value, "counts": counts, "ai_providers": ai_providers}
        module_summary = getattr(program_ir, "module_summary", None)
        if module_summary:
            payload["module_summary"] = module_summary
        matrix = build_capability_matrix()
        report = evaluate_graduation(matrix)
        payload["graduation"] = {
            "summary": matrix.get("summary", {}),
            "capabilities": matrix.get("capabilities", []),
            "summary_lines": render_summary_lines(matrix),
            "matrix_lines": render_matrix_lines(matrix),
            "graduation_lines": render_graduation_lines(report),
            "report": {
                "ai_language_ready": report.ai_language_ready,
                "beta_ready": report.beta_ready,
                "missing_ai_language": list(report.missing_ai_language),
                "missing_beta": list(report.missing_beta),
            },
        }
        return payload
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="parse", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")


def get_ui_payload(source: str, session: SessionState | None = None, app_path: str | None = None) -> dict:
    try:
        session = session or SessionState()
        app_file = _require_app_path(app_path)
        program_ir = _load_project_program(source, app_file.as_posix())
        config = load_config(app_path=app_file)
        warnings: list[ValidationWarning] = []
        identity = resolve_identity(
            config,
            getattr(program_ir, "identity", None),
            mode=ValidationMode.STATIC,
            warnings=warnings,
        )
        store = session.ensure_store(config)
        preference_store = preference_store_for_app(app_path, getattr(program_ir, "theme_preference", {}).get("persist"))
        persisted, _ = preference_store.load_theme(app_pref_key(app_path))
        runtime_theme = session.runtime_theme or persisted or getattr(program_ir, "theme", "system")
        session.runtime_theme = runtime_theme
        manifest = build_manifest(
            program_ir,
            state=session.state,
            store=store,
            runtime_theme=runtime_theme,
            persisted_theme=persisted,
            identity=identity,
            mode=ValidationMode.STATIC,
            warnings=warnings,
        )
        if warnings:
            manifest["warnings"] = [warning.to_dict() for warning in warnings]
        return manifest
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="parse", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")


def get_actions_payload(source: str, app_path: str | None = None) -> dict:
    try:
        app_file = _require_app_path(app_path)
        program_ir = _load_project_program(source, app_file.as_posix())
        config = load_config(app_path=app_file)
        warnings: list[ValidationWarning] = []
        identity = resolve_identity(
            config,
            getattr(program_ir, "identity", None),
            mode=ValidationMode.STATIC,
            warnings=warnings,
        )
        manifest = build_manifest(
            program_ir,
            state={},
            store=MemoryStore(),
            identity=identity,
            mode=ValidationMode.STATIC,
            warnings=warnings,
        )
        data = _actions_from_manifest(manifest)
        payload = {"ok": True, "count": len(data), "actions": data}
        if warnings:
            payload["warnings"] = [warning.to_dict() for warning in warnings]
        return payload
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="parse", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")


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
        return build_error_from_exception(err, kind="tools", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")


def get_secrets_payload(source: str, app_path: str) -> dict:
    try:
        app_file = Path(app_path)
        project = load_project(app_file, source_overrides={app_file: source})
        config = load_config(app_path=project.app_path, root=project.app_path.parent)
        target = _resolve_target(project.app_path.parent)
        refs = discover_required_secrets(project.program, config, target=target, app_path=project.app_path)
        return {
            "ok": True,
            "schema_version": 1,
            "target": target,
            "secrets": [
                {"name": ref.name, "available": ref.available, "source": ref.source, "target": ref.target}
                for ref in refs
            ],
        }
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="parse", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")


def get_diagnostics_payload(source: str, app_path: str) -> dict:
    try:
        program_ir = _load_project_program(source, app_path)
        diagnostics = collect_ai_context_diagnostics(program_ir)
        return {"ok": True, "schema_version": 1, "diagnostics": diagnostics}
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="diagnostics", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")


def get_version_payload() -> dict:
    return {"ok": True, "version": get_version()}


def get_agents_payload_wrapper(source: str, session: SessionState | None, app_path: str | None = None) -> dict:
    app_file = _require_app_path(app_path)
    return get_agents_payload(source, session, app_file.as_posix())


def run_agent_payload_wrapper(source: str, session: SessionState | None, payload: dict, app_path: str | None = None) -> dict:
    app_file = _require_app_path(app_path)
    return run_agent_payload(source, session, app_file.as_posix(), payload)


def run_handoff_payload_wrapper(source: str, session: SessionState | None, payload: dict, app_path: str | None = None) -> dict:
    app_file = _require_app_path(app_path)
    return run_handoff_action(source, session, app_file.as_posix(), payload)


def apply_agent_wizard_wrapper(source: str, payload: dict, app_path: str | None = None) -> dict:
    app_file = _require_app_path(app_path)
    return apply_agent_wizard(source, app_file.as_posix(), payload)


def update_memory_packs_wrapper(source: str, session: SessionState | None, payload: dict, app_path: str | None = None) -> dict:
    app_file = _require_app_path(app_path)
    return update_memory_packs(source, session, app_file.as_posix(), payload)


def execute_action(source: str, session: SessionState | None, action_id: str, payload: dict, app_path: str | None = None) -> dict:
    app_file: Path | None = None
    config = None
    try:
        session = session or SessionState()
        app_file = _require_app_path(app_path)
        program_ir = _load_project_program(source, app_file.as_posix())
        config = load_config(app_path=app_file)
        store = session.ensure_store(config)
        response = handle_action(
            program_ir,
            action_id=action_id,
            payload=payload,
            state=session.state,
            store=store,
            runtime_theme=session.runtime_theme or getattr(program_ir, "theme", "system"),
            preference_store=preference_store_for_app(app_path, getattr(program_ir, "theme_preference", {}).get("persist")),
            preference_key=app_pref_key(app_path),
            allow_theme_override=getattr(program_ir, "theme_preference", {}).get("allow_override"),
            config=config,
            memory_manager=session.memory_manager,
            source=source,
            raise_on_error=False,
        )
        if response and isinstance(response, dict):
            ui_theme = (response.get("ui") or {}).get("theme") if response.get("ui") else None
            if ui_theme and ui_theme.get("current"):
                session.runtime_theme = ui_theme.get("current")
        if response and isinstance(response, dict):
            return normalize_action_response(response)
        return response
    except Namel3ssError as err:
        error_payload = build_error_from_exception(err, kind="engine", source=source)
        contract_payload = build_run_payload(
            ok=False,
            flow_name=None,
            state={},
            result=None,
            traces=[],
            project_root=app_file.parent if app_file else None,
            error=err,
            error_payload=error_payload,
        )
        if config is not None:
            secret_values = collect_secret_values(config)
        else:
            secret_values = collect_secret_values()
        redacted = finalize_run_payload(contract_payload, secret_values)
        normalized = normalize_action_response(redacted)
        return normalized
    except Exception as err:  # pragma: no cover - defensive guard rail
        error_payload = build_error_payload(str(err), kind="internal")
        contract_payload = build_run_payload(
            ok=False,
            flow_name=None,
            state={},
            result=None,
            traces=[],
            project_root=app_file.parent if app_file else None,
            error=err,
            error_payload=error_payload,
        )
        secret_values = collect_secret_values(config) if config is not None else collect_secret_values()
        redacted = finalize_run_payload(contract_payload, secret_values)
        normalized = normalize_action_response(redacted)
        return normalized


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


def _resolve_target(project_root: Path) -> str:
    state = load_state(project_root)
    active = state.get("active") or {}
    return parse_target(active.get("target")).name


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


def _require_app_path(app_path: str | None) -> Path:
    if app_path:
        return Path(app_path)
    raise Namel3ssError(
        build_guidance_message(
            what="Studio needs an app file path to resolve tools/ bindings.",
            why="tools.yaml and tools/ require a project root.",
            fix="Run Studio from the folder that contains app.ai or pass the path explicitly.",
            example="cd <project-root> && n3 studio app.ai",
        )
    )
