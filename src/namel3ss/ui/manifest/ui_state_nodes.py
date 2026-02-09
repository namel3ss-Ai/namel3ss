from __future__ import annotations

from copy import deepcopy

from namel3ss.ir import nodes as ir


_SCOPE_ORDER = ("ephemeral", "session", "persistent")


def build_ui_state_payload(
    program: ir.Program,
    *,
    state_base: dict,
) -> dict | None:
    declaration = getattr(program, "ui_state", None)
    if not isinstance(declaration, ir.UIStateDecl):
        return None
    state_ui = state_base.get("ui") if isinstance(state_base, dict) else None
    state_ui_values = state_ui if isinstance(state_ui, dict) else {}
    scopes_payload: dict[str, list[dict]] = {}
    values_payload: dict[str, dict] = {}
    fields_payload: list[dict] = []
    for scope in _SCOPE_ORDER:
        fields = list(getattr(declaration, scope, None) or [])
        if not fields:
            continue
        scope_fields: list[dict] = []
        scope_values: dict[str, object] = {}
        for field in fields:
            key = str(getattr(field, "key", "") or "")
            if not key:
                continue
            restored = key in state_ui_values
            value = deepcopy(state_ui_values.get(key)) if restored else deepcopy(getattr(field, "default_value", None))
            source = "restored" if restored else "default"
            entry = {
                "key": key,
                "path": f"state.ui.{key}",
                "type": str(getattr(field, "type_name", "") or ""),
                "scope": scope,
                "source": source,
            }
            scope_fields.append(entry)
            scope_values[key] = value
            fields_payload.append(entry)
        if scope_fields:
            scopes_payload[scope] = scope_fields
            values_payload[scope] = scope_values
    if not scopes_payload:
        return None
    return {
        "scopes": scopes_payload,
        "values": values_payload,
        "fields": fields_payload,
    }


__all__ = ["build_ui_state_payload"]
