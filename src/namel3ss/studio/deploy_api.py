from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import resolve_config
from namel3ss.module_loader import load_project
from namel3ss.runtime.deploy_routes import get_build_payload, get_deploy_payload


def get_build_payload_from_source(source: str, app_path: str) -> dict:
    app_file = Path(app_path)
    config, sources = resolve_config(app_path=app_file, root=app_file.parent)
    return get_build_payload(app_file.parent, app_file, config=config, sources=sources)


def get_deploy_payload_from_source(source: str, app_path: str) -> dict:
    app_file = Path(app_path)
    project = load_project(app_file, source_overrides={app_file: source})
    config, sources = resolve_config(app_path=app_file, root=app_file.parent)
    return get_deploy_payload(
        app_file.parent,
        app_file,
        program=project.program,
        config=config,
        sources=sources,
    )


__all__ = ["get_build_payload_from_source", "get_deploy_payload_from_source"]
