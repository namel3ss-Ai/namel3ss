from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.format.formatter import format_source
from namel3ss.ir import nodes as ir
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.studio.edit.selectors import find_element, find_line_number
from namel3ss.studio.edit.transform import replace_literal_at_line
from namel3ss.studio.session import SessionState
from namel3ss.ui.manifest import build_manifest

SUPPORTED_OPS = {"set_title", "set_text", "set_button_label"}


def apply_edit_to_source(
    source: str,
    op: str,
    target: dict,
    value: str,
    session: SessionState | None = None,
) -> tuple[str, ir.Program, dict]:
    if op not in SUPPORTED_OPS:
        raise Namel3ssError(f"Unsupported edit op '{op}'")
    if not isinstance(target, dict):
        raise Namel3ssError("Edit target must be an object")
    page_name = target.get("page")
    element_id = target.get("element_id")
    if not isinstance(page_name, str) or not isinstance(element_id, str):
        raise Namel3ssError("Edit target must include 'page' and 'element_id'")
    if not isinstance(value, str):
        raise Namel3ssError("Edit value must be a string")

    program_ir = _lower(source)
    manifest = build_manifest(program_ir, state=_session_state(session), store=_session_store(session))
    element, page = find_element(manifest, element_id)
    if page.get("name") != page_name:
        raise Namel3ssError(f"Element '{element_id}' does not belong to page '{page_name}'")

    old_text = _element_value_for_op(element, op)
    line_no = find_line_number(source, page_name, element)
    updated_source = replace_literal_at_line(source, line_no, old_text, value)
    formatted = format_source(updated_source)
    updated_ir = _lower(formatted)
    updated_manifest = build_manifest(updated_ir, state=_session_state(session), store=_session_store(session))
    return formatted, updated_ir, updated_manifest


def _lower(source: str):
    ast_program = parse(source)
    return lower_program(ast_program)


def _element_value_for_op(element: dict, op: str) -> str | None:
    if op == "set_title":
        if element.get("type") != "title":
            raise Namel3ssError("Target is not a title item")
        return element.get("value")
    if op == "set_text":
        if element.get("type") != "text":
            raise Namel3ssError("Target is not a text item")
        return element.get("value")
    if op == "set_button_label":
        if element.get("type") != "button":
            raise Namel3ssError("Target is not a button item")
        return element.get("label")
    return None


def _session_state(session: SessionState | None) -> dict:
    if session is None:
        return {}
    return session.state


def _session_store(session: SessionState | None) -> MemoryStore | None:
    if session is None:
        return None
    return session.store
