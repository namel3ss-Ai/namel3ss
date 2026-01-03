from __future__ import annotations

from pathlib import Path
import json

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.preferences.factory import preference_store_for_app, app_pref_key
from namel3ss.runtime.run_pipeline import build_flow_payload, finalize_run_payload
from namel3ss.secrets import collect_secret_values
from namel3ss.utils.json_tools import dumps as json_dumps


def run_flow(
    program_ir,
    flow_name: str | None = None,
    *,
    sources: dict | None = None,
    source: str | None = None,
) -> dict:
    selected = _select_flow(program_ir, flow_name)
    app_path = getattr(program_ir, "app_path", None)
    source_text = source or _resolve_source(sources, app_path)
    pref_store = preference_store_for_app(app_path, getattr(program_ir, "theme_preference", {}).get("persist"))
    config = load_config(
        app_path=app_path,
        root=getattr(program_ir, "project_root", None),
    )
    secret_values = collect_secret_values(config)
    outcome = build_flow_payload(
        program_ir,
        selected,
        state={},
        input={},
        store=None,
        runtime_theme=getattr(program_ir, "theme", None),
        preference_store=pref_store,
        preference_key=app_pref_key(app_path),
        config=config,
        source=source_text,
        project_root=getattr(program_ir, "project_root", None),
    )
    payload = finalize_run_payload(outcome.payload, secret_values)
    _write_last_run(program_ir, payload)
    if outcome.error:
        raise outcome.error
    return payload


def _select_flow(program_ir, flow_name: str | None) -> str:
    public_flows = getattr(program_ir, "public_flows", None)
    entry_flows = getattr(program_ir, "entry_flows", None)
    if flow_name:
        if public_flows and flow_name not in public_flows:
            raise Namel3ssError(_unknown_flow_message(flow_name, public_flows))
        return flow_name
    candidates = entry_flows or [flow.name for flow in program_ir.flows]
    if len(candidates) == 1:
        return candidates[0]
    raise Namel3ssError('Multiple flows found. Use: n3 app.ai flow "flow_name"')


def _unknown_flow_message(flow_name: str, flows: list[str]) -> str:
    available = flows
    sample = ", ".join(available[:5]) if available else "none defined"
    if len(available) > 5:
        sample += ", ..."
    why = f"The app defines flows: {sample}."
    if not available:
        why = "The app does not define any flows."
    example = f'n3 app.ai flow "{available[0]}"' if available else 'flow "demo": return "ok"'
    return build_guidance_message(
        what=f"Unknown flow '{flow_name}'.",
        why=why,
        fix="Call an existing flow or add it to your app.ai file.",
        example=example,
    )


def _resolve_source(sources: dict | None, app_path: object) -> str | None:
    if not sources:
        return None
    if app_path is not None:
        for key, value in sources.items():
            if key == app_path or str(key) == str(app_path):
                return value
    return next(iter(sources.values()), None)


def _write_last_run(program_ir, payload: dict) -> None:
    project_root = getattr(program_ir, "project_root", None)
    if not project_root:
        return
    root = Path(project_root)
    run_dir = root / ".namel3ss" / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    last_json = run_dir / "last.json"
    last_json.write_text(json_dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_last_error_pack(program_ir) -> None:
    project_root = getattr(program_ir, "project_root", None)
    if not project_root:
        return
    errors_dir = Path(project_root) / ".namel3ss" / "errors"
    last_json = errors_dir / "last.json"
    last_plain = errors_dir / "last.plain"
    if last_json.exists() and last_plain.exists():
        return


def _error_step_id(program_ir) -> str | None:
    project_root = getattr(program_ir, "project_root", None)
    if not project_root:
        return None
    path = Path(project_root) / ".namel3ss" / "execution" / "last.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    steps = data.get("execution_steps") or []
    if not isinstance(steps, list):
        return None
    for step in reversed(steps):
        if isinstance(step, dict) and step.get("kind") == "error" and step.get("id"):
            return str(step.get("id"))
    return None
