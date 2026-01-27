from __future__ import annotations

from namel3ss.runtime.flow.ids import flow_step_id
from namel3ss.runtime.identity.guards import GuardContext
from namel3ss.runtime.mutation_policy import evaluate_mutation_policy_for_rule
from namel3ss.traces.schema import TraceEventType
from namel3ss.runtime.ui.actions.model import (
    form_flow_name,
    page_decl_for_name,
    page_name_for_slug,
    page_slug_from_action,
    page_subject,
)


def submit_form_trace(record: str, values: dict) -> dict:
    fields = sorted({str(key) for key in values.keys()})
    return {"type": "submit_form", "record": record, "ok": True, "fields": fields}


def enforce_form_policy(
    program_ir,
    manifest: dict,
    action_id: str,
    record: str,
    payload: dict,
    state: dict,
    identity: dict | None,
    auth_context: object | None,
) -> tuple[dict, object]:
    page_slug = page_slug_from_action(action_id)
    page_name = page_name_for_slug(manifest, page_slug)
    page_decl = page_decl_for_name(program_ir, page_name)
    subject = page_subject(page_name, page_slug)
    flow_name = form_flow_name(page_slug, record)
    step_id = flow_step_id(flow_name, "save", 1)
    ctx = GuardContext(
        locals={"input": payload, "mutation": {"action": "save", "record": record}},
        state=state,
        identity=identity or {},
        auth_context=auth_context,
    )
    decision = evaluate_mutation_policy_for_rule(
        ctx,
        action="save",
        record=record,
        subject=subject,
        requires_expr=getattr(page_decl, "requires", None) if page_decl else None,
        audited=False,
    )
    if decision.allowed:
        entry = {
            "type": TraceEventType.MUTATION_ALLOWED,
            "flow_name": flow_name,
            "step_id": step_id,
            "record": record,
            "action": "save",
        }
        return entry, decision
    entry = {
        "type": TraceEventType.MUTATION_BLOCKED,
        "flow_name": flow_name,
        "step_id": step_id,
        "record": record,
        "action": "save",
        "reason_code": decision.reason_code,
        "message": decision.message,
        "fix_hint": decision.fix_hint,
    }
    return entry, decision


__all__ = ["enforce_form_policy", "submit_form_trace"]
