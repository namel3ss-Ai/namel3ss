from __future__ import annotations

from pathlib import Path
from typing import Dict

from namel3ss.cli.demo_support import is_demo_project
from namel3ss.runtime.executor import execute_program_flow


def summarize_program(program_ir) -> Dict[str, object]:
    return {
        "flows": sorted(flow.name for flow in getattr(program_ir, "flows", [])),
        "pages": sorted(getattr(page, "name", "") for page in getattr(program_ir, "pages", []) if getattr(page, "name", "")),
        "records": sorted(getattr(rec, "name", "") for rec in getattr(program_ir, "records", []) if getattr(rec, "name", "")),
    }


def contract_kind_for_path(path: str) -> str | None:
    if path in {"/api/ui/contract", "/api/ui/contract.json"}:
        return "all"
    if path in {"/api/ui/contract/ui", "/api/ui/contract/ui.json"}:
        return "ui"
    if path in {"/api/ui/contract/actions", "/api/ui/contract/actions.json"}:
        return "actions"
    if path in {"/api/ui/contract/schema", "/api/ui/contract/schema.json"}:
        return "schema"
    return None


def should_auto_seed(program_ir, enabled: bool, flow_name: str) -> bool:
    if not enabled or not flow_name:
        return False
    flows = [flow.name for flow in getattr(program_ir, "flows", []) if getattr(flow, "name", None)]
    if flow_name not in flows:
        return False
    project_root = resolve_project_root(program_ir)
    if not project_root:
        return False
    return is_demo_project(project_root)


def resolve_project_root(program_ir) -> Path | None:
    root = getattr(program_ir, "project_root", None)
    if isinstance(root, Path):
        return root
    if isinstance(root, str) and root:
        return Path(root)
    app_path = getattr(program_ir, "app_path", None)
    if isinstance(app_path, Path):
        return app_path.parent
    if isinstance(app_path, str) and app_path:
        return Path(app_path).parent
    return None


def seed_flow(program_ir, flow_name: str) -> None:
    try:
        execute_program_flow(program_ir, flow_name)
    except Exception:
        pass


__all__ = [
    "contract_kind_for_path",
    "resolve_project_root",
    "seed_flow",
    "should_auto_seed",
    "summarize_program",
]
