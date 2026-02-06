from __future__ import annotations

from pathlib import Path
from typing import Callable

from namel3ss.config.security_compliance import (
    AuthConfig,
    RetentionConfig,
    SecurityConfig,
    auth_config_path,
    load_auth_config,
    load_retention_config,
    load_security_config,
    retention_config_path,
    security_config_path,
)
from namel3ss.errors.base import Namel3ssError
from namel3ss.module_loader import load_project
from namel3ss.runtime.mutation_policy import flow_mutates, page_has_form


def build_security_status(project_root: str | Path | None, app_path: str | Path | None) -> dict[str, object]:
    app_file = Path(app_path).resolve() if app_path is not None else None
    root = Path(project_root).resolve() if project_root is not None else (app_file.parent if app_file else None)
    configs, config_violations = _config_payload(root, app_file)
    requires_payload, requires_violations = _requires_payload(app_file)
    violations = sorted(
        [*config_violations, *requires_violations],
        key=lambda item: (
            str(item.get("code") or ""),
            str(item.get("entity") or ""),
            str(item.get("name") or ""),
        ),
    )
    return {
        "ok": len(violations) == 0,
        "configured": {
            "auth": bool(configs["auth"].get("configured")),
            "security": bool(configs["security"].get("configured")),
            "retention": bool(configs["retention"].get("configured")),
        },
        "configs": configs,
        "requires": requires_payload,
        "violations": violations,
        "count": len(violations),
    }


def _config_payload(project_root: Path | None, app_path: Path | None) -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
    auth_payload, auth_violations = _single_config_payload(
        "auth",
        project_root,
        app_path,
        load_auth_config,
        auth_config_path,
    )
    security_payload, security_violations = _single_config_payload(
        "security",
        project_root,
        app_path,
        load_security_config,
        security_config_path,
    )
    retention_payload, retention_violations = _single_config_payload(
        "retention",
        project_root,
        app_path,
        load_retention_config,
        retention_config_path,
    )
    return (
        {
            "auth": auth_payload,
            "security": security_payload,
            "retention": retention_payload,
        },
        [*auth_violations, *security_violations, *retention_violations],
    )


def _single_config_payload(
    config_name: str,
    project_root: Path | None,
    app_path: Path | None,
    loader: Callable[[str | Path | None, str | Path | None], AuthConfig | SecurityConfig | RetentionConfig | None],
    path_resolver: Callable[[str | Path | None, str | Path | None], Path | None],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    path = path_resolver(project_root, app_path)
    exists = path.exists() if path is not None else False
    payload: dict[str, object] = {
        "configured": bool(exists),
        "path": path.as_posix() if path is not None else "",
        "config": None,
    }
    violations: list[dict[str, object]] = []
    try:
        parsed = loader(project_root, app_path)
    except Namel3ssError as err:
        payload["error"] = err.message
        violations.append(
            {
                "code": "config.invalid",
                "entity": "config",
                "name": config_name,
                "message": err.message,
            }
        )
        return payload, violations
    if parsed is not None:
        payload["config"] = parsed.to_dict()
    return payload, violations


def _requires_payload(app_path: Path | None) -> tuple[dict[str, object], list[dict[str, object]]]:
    payload: dict[str, object] = {
        "mutating_flows": [],
        "unguarded_flows": [],
        "mutating_pages": [],
        "unguarded_pages": [],
    }
    violations: list[dict[str, object]] = []
    if app_path is None:
        payload["error"] = "App path is missing."
        violations.append(
            {
                "code": "program.missing",
                "entity": "app",
                "name": "",
                "message": "App path is missing.",
            }
        )
        return payload, violations
    try:
        project = load_project(app_path)
    except Namel3ssError as err:
        payload["error"] = err.message
        violations.append(
            {
                "code": "program.invalid",
                "entity": "app",
                "name": app_path.name,
                "message": err.message,
            }
        )
        return payload, violations

    mutating_flows = sorted(
        [flow.name for flow in project.program.flows if flow_mutates(flow)],
        key=str,
    )
    unguarded_flows = sorted(
        [flow.name for flow in project.program.flows if flow_mutates(flow) and flow.requires is None],
        key=str,
    )
    mutating_pages = sorted(
        [page.name for page in project.program.pages if page_has_form(page)],
        key=str,
    )
    unguarded_pages = sorted(
        [page.name for page in project.program.pages if page_has_form(page) and page.requires is None],
        key=str,
    )

    for flow_name in unguarded_flows:
        violations.append(
            {
                "code": "requires.flow_missing",
                "entity": "flow",
                "name": flow_name,
                "message": f'Flow "{flow_name}" mutates data without requires.',
            }
        )
    for page_name in unguarded_pages:
        violations.append(
            {
                "code": "requires.page_missing",
                "entity": "page",
                "name": page_name,
                "message": f'Page "{page_name}" has a form without requires.',
            }
        )

    payload.update(
        {
            "mutating_flows": mutating_flows,
            "unguarded_flows": unguarded_flows,
            "mutating_pages": mutating_pages,
            "unguarded_pages": unguarded_pages,
            "mutating_flow_count": len(mutating_flows),
            "unguarded_flow_count": len(unguarded_flows),
            "mutating_page_count": len(mutating_pages),
            "unguarded_page_count": len(unguarded_pages),
        }
    )
    return payload, violations


__all__ = ["build_security_status"]
