from __future__ import annotations

from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.state_defaults import StateContext


def build_chat_composer_manifest(
    item: ir.ChatComposerItem,
    *,
    element_id: str,
    page_name: str,
    page_slug: str,
    index: int,
    state_ctx: StateContext,
) -> tuple[dict, dict]:
    action_id = f"{element_id}.composer"
    fields = _composer_fields(item)
    composer_shell = _composer_shell_contract(item, state_ctx=state_ctx)
    action_type = "chat.message.send" if composer_shell is not None else "call_flow"
    action_payload = {"type": action_type, "flow": item.flow_name}
    if fields:
        action_payload["fields"] = fields
    element = {
        "type": "composer",
        "flow": item.flow_name,
        "action_type": action_type,
        "id": action_id,
        "action_id": action_id,
        "action": action_payload,
        "element_id": element_id,
        "page": page_name,
        "page_slug": page_slug,
        "index": index,
        "line": item.line,
        "column": item.column,
    }
    if fields:
        element["fields"] = fields
    if composer_shell is not None:
        element["composer_state"] = composer_shell["state"]
        element["composer_state_source"] = composer_shell["source"]
    action_entry = {"id": action_id, "type": action_type, "flow": item.flow_name}
    if fields:
        action_entry["fields"] = fields
    return element, {action_id: action_entry}


def _composer_fields(item: ir.ChatComposerItem) -> list[dict] | None:
    extra_fields = list(getattr(item, "fields", []) or [])
    if not extra_fields:
        return None
    fields: list[dict] = [{"name": "message", "type": "text"}]
    for field in extra_fields:
        fields.append({"name": field.name, "type": field.type_name})
    return fields


def _composer_shell_contract(item: ir.ChatComposerItem, *, state_ctx: StateContext) -> dict | None:
    path = _composer_shell_state_path(item)
    if not path:
        return None
    value, _ = state_ctx.value(path, default={}, register_default=True)
    return {
        "source": f"state.{'.'.join(path)}",
        "state": _normalize_composer_shell_state(value),
    }


def _composer_shell_state_path(item: ir.ChatComposerItem) -> list[str] | None:
    origin = getattr(item, "origin", None)
    if not isinstance(origin, dict):
        return None
    rag_origin = origin.get("rag_ui")
    if not isinstance(rag_origin, dict):
        return None
    if rag_origin.get("binding") != "composer_state":
        return None
    path = rag_origin.get("state_path")
    if not isinstance(path, list):
        return None
    values = [str(entry).strip() for entry in path if isinstance(entry, str) and entry.strip()]
    return values or None


def _normalize_composer_shell_state(value: object) -> dict:
    if not isinstance(value, dict):
        return {"attachments": [], "draft": "", "tools": [], "web_search": False}
    return {
        "attachments": _normalize_composer_text_list(value.get("attachments")),
        "draft": str(value.get("draft") or ""),
        "tools": _normalize_composer_text_list(value.get("tools")),
        "web_search": bool(value.get("web_search")),
    }


def _normalize_composer_text_list(value: object) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in values:
        if not isinstance(entry, str):
            continue
        text = entry.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


__all__ = ["build_chat_composer_manifest"]
