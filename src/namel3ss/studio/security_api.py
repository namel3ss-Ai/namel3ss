from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.config.overrides import write_capability_overrides
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.module_loader import load_project
from namel3ss.runtime.capabilities.report import collect_tool_reports
from namel3ss.runtime.capabilities.validate import normalize_overrides
from namel3ss.runtime.tools.bindings import load_tool_bindings, write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding


def get_security_payload(app_path: str) -> dict:
    app_file = Path(app_path)
    try:
        source = app_file.read_text(encoding="utf-8")
    except Exception:
        source = ""
    try:
        project = load_project(app_file)
        app_root = project.app_path.parent
        config = load_config(app_path=project.app_path, root=app_root)
        reports = collect_tool_reports(app_root, config, project.program.tools)
        overrides = dict(config.capability_overrides)
        for report in reports:
            tool_name = report.get("tool_name")
            if isinstance(tool_name, str):
                report["overrides"] = overrides.get(tool_name, {})
        return {
            "ok": True,
            "app_root": str(app_root),
            "tools": reports,
            "overrides": overrides,
        }
    except Namel3ssError as err:
        return {"ok": False, "error": format_error(err, source)}


def apply_security_override(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Body must be a JSON object"}
    tool_name = payload.get("tool_name")
    overrides = payload.get("overrides")
    if not isinstance(tool_name, str) or not tool_name:
        return {"ok": False, "error": "tool_name is required"}
    if overrides is None:
        overrides = {}
    if not isinstance(overrides, dict):
        return {"ok": False, "error": "overrides must be an object"}
    try:
        normalized = normalize_overrides(overrides, label=f'"{tool_name}"')
    except Namel3ssError as err:
        return {"ok": False, "error": str(err)}

    app_file = Path(app_path)
    try:
        project = load_project(app_file)
        app_root = project.app_path.parent
        config = load_config(app_path=project.app_path, root=app_root)
        updated = dict(config.capability_overrides)
        if normalized:
            updated[tool_name] = normalized
        else:
            updated.pop(tool_name, None)
        path = write_capability_overrides(app_root, updated)
        return {"ok": True, "tool_name": tool_name, "config_path": str(path), "overrides": updated}
    except Namel3ssError as err:
        return {"ok": False, "error": str(err)}


def apply_security_sandbox(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Body must be a JSON object"}
    tool_name = payload.get("tool_name")
    enabled = payload.get("enabled")
    if not isinstance(tool_name, str) or not tool_name:
        return {"ok": False, "error": "tool_name is required"}
    if not isinstance(enabled, bool):
        return {"ok": False, "error": "enabled must be true or false"}
    app_file = Path(app_path)
    try:
        project = load_project(app_file)
        app_root = project.app_path.parent
        bindings = load_tool_bindings(app_root)
        binding = bindings.get(tool_name)
        if binding is None:
            return {"ok": False, "error": "Tool is not bound in tools.yaml"}
        updated = ToolBinding(
            kind=binding.kind,
            entry=binding.entry,
            runner=binding.runner,
            url=binding.url,
            image=binding.image,
            command=binding.command,
            env=binding.env,
            purity=binding.purity,
            timeout_ms=binding.timeout_ms,
            sandbox=enabled,
            enforcement=binding.enforcement,
        )
        bindings[tool_name] = updated
        path = write_tool_bindings(app_root, bindings)
        return {
            "ok": True,
            "tool_name": tool_name,
            "sandbox": enabled,
            "bindings_path": str(path),
        }
    except Namel3ssError as err:
        return {"ok": False, "error": str(err)}


__all__ = ["apply_security_override", "apply_security_sandbox", "get_security_payload"]
