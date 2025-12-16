from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.ir.nodes import lower_program
from namel3ss.lint.engine import lint_source
from namel3ss.parser.core import parse
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.studio.edit import apply_edit_to_source
from namel3ss.studio.session import SessionState
from namel3ss.ui.manifest import build_manifest


def _load_program(source: str):
    ast_program = parse(source)
    return lower_program(ast_program)


def get_summary_payload(source: str, path: str) -> dict:
    try:
        program_ir = _load_program(source)
        counts = {
            "records": len(program_ir.records),
            "flows": len(program_ir.flows),
            "pages": len(program_ir.pages),
            "ais": len(program_ir.ais),
            "agents": len(program_ir.agents),
            "tools": len(program_ir.tools),
        }
        return {"ok": True, "file": path, "counts": counts}
    except Namel3ssError as err:
        return {"ok": False, "error": format_error(err, source)}


def get_ui_payload(source: str, session: SessionState | None = None) -> dict:
    try:
        program_ir = _load_program(source)
        manifest = build_manifest(
            program_ir,
            state=session.state if session else {},
            store=session.store if session else MemoryStore(),
        )
        return manifest
    except Namel3ssError as err:
        return {"ok": False, "error": format_error(err, source)}


def get_actions_payload(source: str) -> dict:
    try:
        program_ir = _load_program(source)
        manifest = build_manifest(program_ir, state={}, store=MemoryStore())
        data = _actions_from_manifest(manifest)
        return {"ok": True, "count": len(data), "actions": data}
    except Namel3ssError as err:
        return {"ok": False, "error": format_error(err, source)}


def get_lint_payload(source: str) -> dict:
    findings = lint_source(source)
    return {
        "ok": len(findings) == 0,
        "count": len(findings),
        "findings": [f.to_dict() for f in findings],
    }


def execute_action(source: str, session: SessionState, action_id: str, payload: dict) -> dict:
    program_ir = _load_program(source)
    return handle_action(program_ir, action_id=action_id, payload=payload, state=session.state, store=session.store)


def apply_edit(app_path: str, op: str, target: dict, value: str, session: SessionState) -> dict:
    source_text = Path(app_path).read_text(encoding="utf-8")
    formatted_source, program_ir, manifest = apply_edit_to_source(source_text, op, target, value, session)
    Path(app_path).write_text(formatted_source, encoding="utf-8")
    actions = _actions_from_manifest(manifest)
    lint_payload = get_lint_payload(formatted_source)
    summary = _summary_from_program(program_ir, app_path)
    return {
        "ok": True,
        "ui": manifest,
        "actions": {"ok": True, "count": len(actions), "actions": actions},
        "lint": lint_payload,
        "summary": summary,
    }


def _actions_from_manifest(manifest: dict) -> list[dict]:
    actions = manifest.get("actions", {})
    sorted_ids = sorted(actions.keys())
    data = []
    for action_id in sorted_ids:
        entry = actions[action_id]
        item = {"id": action_id, "type": entry.get("type")}
        if entry.get("type") == "call_flow":
            item["flow"] = entry.get("flow")
        if entry.get("type") == "submit_form":
            item["record"] = entry.get("record")
        data.append(item)
    return data


def _summary_from_program(program_ir, path: str) -> dict:
    counts = {
        "records": len(program_ir.records),
        "flows": len(program_ir.flows),
        "pages": len(program_ir.pages),
        "ais": len(program_ir.ais),
        "agents": len(program_ir.agents),
        "tools": len(program_ir.tools),
    }
    return {"ok": True, "file": path, "counts": counts}
