from __future__ import annotations

import json
from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.ingestion.policy_inspection import inspect_ingestion_policy
from namel3ss.module_loader import load_project
from namel3ss.runtime.browser_state import records_snapshot
from namel3ss.studio.session import SessionState


def get_state_payload(source: str, session: SessionState | None, app_path: str | None = None) -> dict:
    session = session or SessionState()
    app_file = _require_app_path(app_path)
    try:
        project = load_project(app_file, source_overrides={app_file: source})
        program_ir = project.program
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="parse", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")
    try:
        config = load_config(app_path=app_file)
        store = session.ensure_store(config)
        payload = {
            "ok": True,
            "state": _state_snapshot(session.state),
            "records": records_snapshot(program_ir, store, config),
            "policy": inspect_ingestion_policy(
                getattr(program_ir, "project_root", None),
                getattr(program_ir, "app_path", None),
                policy_decl=getattr(program_ir, "policy", None),
            ),
        }
        if session.data_effects:
            payload["effects"] = session.data_effects
        return payload
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="state", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")


def _state_snapshot(state: dict) -> dict:
    try:
        return json.loads(canonical_json_dumps(state, pretty=False, drop_run_keys=False))
    except Exception:
        return {}


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


__all__ = ["get_state_payload"]
