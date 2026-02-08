from __future__ import annotations

from dataclasses import fields, is_dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.ir.model.expressions import StatePath
from namel3ss.runtime.backend.upload_state import normalized_upload_entries


def validate_required_uploads_for_flow(program_ir: ir.Program, flow_name: str, state: dict) -> None:
    required_uploads = _required_upload_names(program_ir)
    if not required_uploads:
        return
    referenced_uploads = _flow_upload_reference_names(program_ir, flow_name)
    if not referenced_uploads:
        return
    missing = [name for name in sorted(required_uploads) if name in referenced_uploads and not _has_upload_entries(state, name)]
    if not missing:
        return
    if len(missing) == 1:
        missing_text = missing[0]
        fix_text = f"Select at least one file in upload '{missing_text}' before submitting."
    else:
        missing_text = ", ".join(missing)
        fix_text = f"Select files for required uploads before submitting: {missing_text}."
    raise Namel3ssError(
        build_guidance_message(
            what=f"Required upload selection is missing: {missing_text}.",
            why=f'Flow "{flow_name}" reads state.uploads and requires files before it can run.',
            fix=fix_text,
            example='upload receipt:\n  required is true',
        )
    )


def _required_upload_names(program_ir: ir.Program) -> set[str]:
    names: set[str] = set()
    for page in getattr(program_ir, "pages", []) or []:
        for item in _walk_page_items(getattr(page, "items", []) or []):
            if not isinstance(item, ir.UploadItem):
                continue
            if bool(getattr(item, "required", False)) and isinstance(item.name, str) and item.name:
                names.add(item.name)
    return names


def _flow_upload_reference_names(program_ir: ir.Program, flow_name: str) -> set[str]:
    flow = _flow_by_name(program_ir, flow_name)
    if flow is None:
        return set()
    names: set[str] = set()
    for value in _walk_tree(flow):
        if not isinstance(value, StatePath):
            continue
        path = value.path if isinstance(value.path, list) else []
        if len(path) < 2 or path[0] != "uploads":
            continue
        upload_name = path[1]
        if isinstance(upload_name, str) and upload_name:
            names.add(upload_name)
    return names


def _has_upload_entries(state: dict, upload_name: str) -> bool:
    try:
        entries = normalized_upload_entries(state, upload_name=upload_name)
    except Namel3ssError:
        return False
    return bool(entries)


def _flow_by_name(program_ir: ir.Program, flow_name: str):
    for flow in getattr(program_ir, "flows", []) or []:
        if getattr(flow, "name", None) == flow_name:
            return flow
    return None


def _walk_page_items(items: list[object]) -> list[object]:
    collected: list[object] = []
    for item in items:
        collected.append(item)
        children = getattr(item, "children", None)
        if isinstance(children, list):
            collected.extend(_walk_page_items(children))
        tabs = getattr(item, "tabs", None)
        if isinstance(tabs, list):
            for tab in tabs:
                tab_children = getattr(tab, "children", None)
                if isinstance(tab_children, list):
                    collected.extend(_walk_page_items(tab_children))
    return collected


def _walk_tree(root: object) -> list[object]:
    stack: list[object] = [root]
    seen: set[int] = set()
    walked: list[object] = []
    while stack:
        current = stack.pop()
        if current is None:
            continue
        if isinstance(current, (str, bytes, int, float, bool)):
            continue
        current_id = id(current)
        if current_id in seen:
            continue
        seen.add(current_id)
        walked.append(current)
        if isinstance(current, dict):
            for value in current.values():
                stack.append(value)
            continue
        if isinstance(current, (list, tuple, set)):
            for value in current:
                stack.append(value)
            continue
        if is_dataclass(current):
            for field in fields(current):
                if field.name in {"line", "column"}:
                    continue
                stack.append(getattr(current, field.name, None))
    return walked


__all__ = ["validate_required_uploads_for_flow"]
