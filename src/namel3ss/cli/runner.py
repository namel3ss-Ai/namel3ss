from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.runtime.preferences.factory import preference_store_for_app, app_pref_key


def run_flow(program_ir, flow_name: str | None = None) -> dict:
    selected = _select_flow(program_ir, flow_name)
    pref_store = preference_store_for_app(None, getattr(program_ir, "theme_preference", {}).get("persist"))
    result = execute_program_flow(
        program_ir,
        selected,
        state={},
        input={},
        store=resolve_store(None),
        runtime_theme=getattr(program_ir, "theme", None),
        preference_store=pref_store,
        preference_key=app_pref_key(None),
    )
    traces = [_trace_to_dict(t) for t in result.traces]
    return {"ok": True, "state": result.state, "result": result.last_value, "traces": traces}


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
    raise Namel3ssError('Multiple flows found; use: n3 <app.ai> flow "<name>"')


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


def _trace_to_dict(trace) -> dict:
    if hasattr(trace, "__dict__"):
        return trace.__dict__
    if isinstance(trace, dict):
        return trace
    return {"trace": trace}
