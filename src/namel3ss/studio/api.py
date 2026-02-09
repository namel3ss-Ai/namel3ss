from __future__ import annotations

from pathlib import Path
from typing import Mapping

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
from namel3ss.runtime.audit.runtime_capture import attach_audit_artifacts
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.answer.traces import extract_answer_explain
from namel3ss.runtime.spec_version import NAMEL3SS_SPEC_VERSION, RUNTIME_SPEC_VERSION
from namel3ss.runtime.browser_state import record_data_effects, record_rows_snapshot
from namel3ss.runtime.auth.auth_context import resolve_auth_context
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.runtime.preferences.factory import preference_store_for_app, app_pref_key
from namel3ss.studio.session import SessionState
from namel3ss.studio.trace_adapter import normalize_action_response
from namel3ss.studio.payload_enrichment import (
    attach_studio_metadata,
    build_diagnostics_payload,
    record_run_artifact,
)
from namel3ss.studio.tool_inventory import resolve_target, tool_inventory_payload
from namel3ss.tools.health.analyze import analyze_tool_health
from namel3ss.validation_entrypoint import build_static_manifest
from namel3ss.ui.settings import UI_ALLOWED_VALUES, UI_DEFAULTS
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
from namel3ss.validation import ValidationWarning


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
    session = session or SessionState()
    app_file = _require_app_path(app_path)
    try:
        program_ir = _load_project_program(source, app_file.as_posix())
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="parse", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")

    try:
        config = load_config(app_path=app_file)
        store = session.ensure_store(config)
        preference_store = preference_store_for_app(app_path, getattr(program_ir, "theme_preference", {}).get("persist"))
        persisted, _ = preference_store.load_theme(app_pref_key(app_path))
        allowed_themes = set(UI_ALLOWED_VALUES.get("theme", ()))
        program_theme = getattr(program_ir, "theme", UI_DEFAULTS["theme"])
        runtime_theme = session.runtime_theme or persisted or program_theme
        if runtime_theme not in allowed_themes:
            runtime_theme = program_theme if program_theme in allowed_themes else UI_DEFAULTS["theme"]
        session.runtime_theme = runtime_theme

        validation_warnings: list[ValidationWarning] = []
        build_static_manifest(
            program_ir,
            config=config,
            state={},
            store=None,
            warnings=validation_warnings,
            runtime_theme=runtime_theme,
            persisted_theme=persisted,
        )

        manifest = build_static_manifest(
            program_ir,
            config=config,
            state=session.state,
            store=store,
            warnings=[],
            runtime_theme=runtime_theme,
            persisted_theme=persisted,
        )
        if validation_warnings:
            manifest["warnings"] = [warning.to_dict() for warning in validation_warnings]
        return attach_studio_metadata(manifest, session)
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="manifest", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")


def get_actions_payload(source: str, app_path: str | None = None) -> dict:
    app_file = _require_app_path(app_path)
    try:
        program_ir = _load_project_program(source, app_file.as_posix())
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="parse", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")

    try:
        config = load_config(app_path=app_file)
        warnings: list[ValidationWarning] = []
        manifest = build_static_manifest(
            program_ir,
            config=config,
            state={},
            store=None,
            warnings=warnings,
        )
        data = _actions_from_manifest(manifest)
        payload = {"ok": True, "count": len(data), "actions": data}
        if warnings:
            payload["warnings"] = [warning.to_dict() for warning in warnings]
        return payload
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="manifest", source=source)
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
        payload = tool_inventory_payload(report, app_root)
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
        target = resolve_target(project.app_path.parent)
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


def get_diagnostics_payload(source: str, session: SessionState | str | None = None, app_path: str | None = None) -> dict:
    resolved_session: SessionState | None = session if isinstance(session, SessionState) else None
    resolved_app_path: str | None
    if isinstance(session, str) and app_path is None:
        resolved_app_path = session
        resolved_session = None
    else:
        resolved_app_path = app_path
    app_file = _require_app_path(resolved_app_path)
    return build_diagnostics_payload(source, resolved_session, app_file.as_posix())


def get_version_payload() -> dict:
    return {
        "ok": True,
        "version": get_version(),
        "spec_version": NAMEL3SS_SPEC_VERSION,
        "runtime_spec_version": RUNTIME_SPEC_VERSION,
    }


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


def execute_action(
    source: str,
    session: SessionState | None,
    action_id: str,
    payload: dict,
    app_path: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> dict:
    app_file: Path | None = None
    config = None
    try:
        session = session or SessionState()
        app_file = _require_app_path(app_path)
        program_ir = _load_project_program(source, app_file.as_posix())
        config = load_config(app_path=app_file)
        store = session.ensure_store(config)
        auth_context = resolve_auth_context(
            headers,
            config=config,
            identity_schema=getattr(program_ir, "identity", None),
            store=store,
            project_root=str(getattr(program_ir, "project_root", "") or "") or None,
            app_path=app_file.as_posix(),
        )
        identity = getattr(auth_context, "identity", None)
        before_rows = record_rows_snapshot(program_ir, store, config, identity=identity)
        response = handle_action(
            program_ir,
            action_id=action_id,
            payload=payload,
            state=session.state,
            store=store,
            runtime_theme=session.runtime_theme or getattr(program_ir, "theme", UI_DEFAULTS["theme"]),
            preference_store=preference_store_for_app(app_path, getattr(program_ir, "theme_preference", {}).get("persist")),
            preference_key=app_pref_key(app_path),
            allow_theme_override=getattr(program_ir, "theme_preference", {}).get("allow_override"),
            config=config,
            identity=identity,
            auth_context=auth_context,
            memory_manager=session.memory_manager,
            source=source,
            raise_on_error=False,
        )
        if isinstance(response, dict):
            response = attach_audit_artifacts(
                response, program_ir=program_ir, config=config, action_id=action_id, input_payload=payload, state_snapshot=response.get("state"), source=source, endpoint="/studio/action"
            )
        session.data_effects = record_data_effects(
            program_ir,
            store,
            config,
            action_id,
            response if isinstance(response, dict) else {},
            before_rows,
            identity=identity,
        )
        if isinstance(response, dict):
            ui_theme = (response.get("ui") or {}).get("theme") if response.get("ui") else None
            if ui_theme and ui_theme.get("current"):
                session.runtime_theme = ui_theme.get("current")
            normalized = normalize_action_response(response)
            explain = extract_answer_explain(normalized.get("traces"))
            if explain is not None:
                session.last_answer_explain = explain
            record_run_artifact(normalized, session)
            return attach_studio_metadata(normalized, session)
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
        secret_values = collect_secret_values(config) if config is not None else collect_secret_values()
        redacted = finalize_run_payload(contract_payload, secret_values)
        normalized = normalize_action_response(redacted)
        return attach_studio_metadata(normalized, session)
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
        return attach_studio_metadata(normalized, session)


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
