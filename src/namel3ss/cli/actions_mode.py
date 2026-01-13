from __future__ import annotations

from namel3ss.config.loader import load_config
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.export.actions import build_actions_list
from namel3ss.validation import ValidationMode


def list_actions(program_ir, json_mode: bool) -> tuple[dict | None, str | None]:
    warnings = []
    config = load_config(
        app_path=getattr(program_ir, "app_path", None),
        root=getattr(program_ir, "project_root", None),
    )
    identity = resolve_identity(
        config,
        getattr(program_ir, "identity", None),
        mode=ValidationMode.STATIC,
        warnings=warnings,
    )
    manifest = build_manifest(
        program_ir,
        state={},
        store=None,
        identity=identity,
        mode=ValidationMode.STATIC,
        warnings=warnings,
    )
    actions = manifest.get("actions", {})
    sorted_ids = sorted(actions.keys())
    if json_mode:
        data = build_actions_list(actions)
        return (
            {
                "ok": True,
                "count": len(data),
                "actions": data,
                **({"warnings": [warning.to_dict() for warning in warnings]} if warnings else {}),
            },
            None,
        )
    lines = []
    for action_id in sorted_ids:
        entry = actions[action_id]
        details: list[str] = []
        if entry.get("type") == "call_flow" and entry.get("flow"):
            details.append(f"flow={entry['flow']}")
        if entry.get("type") == "submit_form" and entry.get("record"):
            details.append(f"record={entry['record']}")
        detail_str = f"  {' '.join(details)}" if details else ""
        lines.append(f"{action_id}  {entry.get('type')} {detail_str}".rstrip())
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in warnings:
            runtime_note = " (enforced at runtime)" if warning.enforced_at else ""
            lines.append(f"- {warning.code}: {warning.message}{runtime_note}")
    return None, "\n".join(lines)
