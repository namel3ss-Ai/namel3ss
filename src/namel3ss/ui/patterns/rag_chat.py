from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Iterable, Mapping

from namel3ss.errors.base import Namel3ssError


RAG_PATTERNS_CAPABILITY = "ui.rag_patterns"
_STATE_PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")


@dataclass(frozen=True)
class RagChatPatternConfig:
    name: str = "rag_chat"
    title: str = "RAG Chat"
    document_state_path: str = "chatState.documents"
    selected_document_state_path: str = "chatState.selectedDocumentId"
    message_state_path: str = "chatState.messages"
    streaming_state_path: str = "chatState.streaming"
    citation_state_path: str = "chatState.citations"
    selected_citation_state_path: str = "chatState.selectedCitationId"
    ingestion_status_state_path: str = "ingestionState.status"
    explain_entries_state_path: str = "chatState.explainEntries"
    show_explain_mode: bool = True


def build_rag_chat_pattern(
    config: RagChatPatternConfig | None = None,
    *,
    capabilities: Iterable[str] | None = None,
    studio_mode: bool = False,
) -> dict[str, object]:
    resolved = config or RagChatPatternConfig()
    _validate_state_paths(resolved)
    capability_set = {str(item).strip().lower() for item in capabilities or []}
    _ensure_rag_capability(capability_set, studio_mode=studio_mode)
    pattern_slug = _slugify(resolved.name)

    ids = _pattern_ids(pattern_slug)
    action_map = _build_action_map(pattern_slug=pattern_slug, ids=ids, config=resolved)

    right_pane_children: list[dict[str, object]] = [
        {
            "type": "component.citation_panel",
            "id": ids["citation_panel"],
            "title": "Sources",
            "citations_state": resolved.citation_state_path,
            "selected_citation_state": resolved.selected_citation_state_path,
            "bindings": {
                "on_click": ids["action_citation_open"],
                "keyboard_shortcut": None,
                "selected_item": resolved.selected_citation_state_path,
            },
            "line": 0,
            "column": 0,
        }
    ]
    if resolved.show_explain_mode:
        right_pane_children.append(
            {
                "type": "component.explain_mode",
                "id": ids["explain_mode"],
                "title": "Explain",
                "entries_state": resolved.explain_entries_state_path,
                "studio_only": True,
                "bindings": {
                    "on_click": None,
                    "keyboard_shortcut": None,
                    "selected_item": None,
                },
                "line": 0,
                "column": 0,
            }
        )

    fragment = {
        "pattern": "rag_chat",
        "capability": RAG_PATTERNS_CAPABILITY,
        "name": resolved.name,
        "title": resolved.title,
        "state": _state_contract(resolved),
        "layout": [
            {
                "type": "layout.main",
                "id": ids["main"],
                "bindings": {"on_click": None, "keyboard_shortcut": None, "selected_item": None},
                "children": [
                    {
                        "type": "layout.three_pane",
                        "id": ids["three_pane"],
                        "bindings": {"on_click": None, "keyboard_shortcut": None, "selected_item": None},
                        "left": [
                            {
                                "type": "component.document_library",
                                "id": ids["document_library"],
                                "title": "Documents",
                                "documents_state": resolved.document_state_path,
                                "selected_document_state": resolved.selected_document_state_path,
                                "bindings": {
                                    "on_click": ids["action_document_select"],
                                    "keyboard_shortcut": None,
                                    "selected_item": resolved.selected_document_state_path,
                                },
                                "line": 0,
                                "column": 0,
                            }
                        ],
                        "center": [
                            {
                                "type": "component.chat_thread",
                                "id": ids["chat_thread"],
                                "title": "Conversation",
                                "messages_state": resolved.message_state_path,
                                "streaming_state": resolved.streaming_state_path,
                                "citations_state": resolved.citation_state_path,
                                "bindings": {
                                    "on_click": ids["action_chat_send"],
                                    "keyboard_shortcut": "ctrl+enter",
                                    "selected_item": None,
                                },
                                "line": 0,
                                "column": 0,
                            },
                            {
                                "type": "layout.sticky",
                                "id": ids["composer_sticky"],
                                "position": "bottom",
                                "visible": True,
                                "bindings": {"on_click": None, "keyboard_shortcut": None, "selected_item": None},
                                "children": [
                                    {
                                        "type": "component.ingestion_progress",
                                        "id": ids["ingestion_progress"],
                                        "status_state": resolved.ingestion_status_state_path,
                                        "bindings": {
                                            "on_click": ids["action_ingestion_retry"],
                                            "keyboard_shortcut": None,
                                            "selected_item": None,
                                        },
                                        "line": 0,
                                        "column": 0,
                                    }
                                ],
                                "line": 0,
                                "column": 0,
                            },
                        ],
                        "right": right_pane_children,
                        "line": 0,
                        "column": 0,
                    }
                ],
                "line": 0,
                "column": 0,
            }
        ],
        "actions": action_map,
    }
    validate_rag_chat_pattern(fragment, studio_mode=studio_mode)
    return fragment


def validate_rag_chat_pattern(fragment: Mapping[str, object], *, studio_mode: bool = False) -> None:
    layout = fragment.get("layout")
    if not isinstance(layout, list):
        raise Namel3ssError('rag_chat pattern must provide "layout" as a list.')
    chat_paths: list[tuple[str, bool]] = []
    explain_present = False

    def walk(nodes: list[dict[str, object]], ancestors: tuple[str, ...]) -> None:
        nonlocal explain_present
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_type = str(node.get("type") or "")
            next_ancestors = ancestors + (node_type,)
            if node_type == "component.chat_thread":
                chat_paths.append((str(node.get("id") or ""), "layout.main" in ancestors))
            if node_type == "component.explain_mode":
                explain_present = True
                if node.get("studio_only", True) is True and not studio_mode:
                    continue
            for key in ("children", "primary", "secondary", "left", "center", "right"):
                children = node.get(key)
                if isinstance(children, list):
                    walk([entry for entry in children if isinstance(entry, dict)], next_ancestors)

    walk([entry for entry in layout if isinstance(entry, dict)], tuple())

    if not chat_paths:
        raise Namel3ssError("rag_chat pattern requires at least one component.chat_thread.")
    outside_main = [path for path, within_main in chat_paths if not within_main]
    if outside_main:
        bad_id = outside_main[0] or "<unknown>"
        raise Namel3ssError(
            f'component.chat_thread "{bad_id}" must be nested under layout.main.'
        )
    if explain_present and not studio_mode:
        # The panel is present but still deterministic: it is declared Studio-only by default.
        pass


def _state_contract(config: RagChatPatternConfig) -> list[dict[str, object]]:
    return [
        {"path": config.document_state_path, "default": []},
        {"path": config.selected_document_state_path, "default": None},
        {"path": config.message_state_path, "default": []},
        {"path": config.streaming_state_path, "default": {}},
        {"path": config.citation_state_path, "default": []},
        {"path": config.selected_citation_state_path, "default": None},
        {"path": config.ingestion_status_state_path, "default": {"status": "idle", "percent": 0}},
        {"path": config.explain_entries_state_path, "default": []},
    ]


def _build_action_map(
    *,
    pattern_slug: str,
    ids: Mapping[str, str],
    config: RagChatPatternConfig,
) -> dict[str, dict[str, object]]:
    ordered = [
        (
            ids["action_document_select"],
            {
                "id": ids["action_document_select"],
                "type": "component.document.select",
                "target": config.selected_document_state_path,
                "payload": {"documents_state": config.document_state_path},
                "order": 0,
                "line": 0,
                "column": 0,
            },
        ),
        (
            ids["action_chat_send"],
            {
                "id": ids["action_chat_send"],
                "type": "component.chat.send",
                "target": "flow.chat.send",
                "payload": {"messages_state": config.message_state_path},
                "order": 1,
                "line": 0,
                "column": 0,
            },
        ),
        (
            ids["action_citation_open"],
            {
                "id": ids["action_citation_open"],
                "type": "component.citation.open",
                "target": ids["citation_panel"],
                "payload": {"selected_state": config.selected_citation_state_path},
                "order": 2,
                "line": 0,
                "column": 0,
            },
        ),
        (
            ids["action_ingestion_retry"],
            {
                "id": ids["action_ingestion_retry"],
                "type": "component.ingestion.retry",
                "target": config.ingestion_status_state_path,
                "payload": {"pattern": pattern_slug},
                "order": 3,
                "line": 0,
                "column": 0,
            },
        ),
    ]
    return {action_id: payload for action_id, payload in ordered}


def _pattern_ids(pattern_slug: str) -> dict[str, str]:
    return {
        "main": _stable_id(pattern_slug, "layout.main", (0,)),
        "three_pane": _stable_id(pattern_slug, "layout.three_pane", (0, 0)),
        "document_library": _stable_id(pattern_slug, "component.document_library", (0, 0, 0)),
        "chat_thread": _stable_id(pattern_slug, "component.chat_thread", (0, 0, 1, 0)),
        "composer_sticky": _stable_id(pattern_slug, "layout.sticky", (0, 0, 1, 1)),
        "ingestion_progress": _stable_id(pattern_slug, "component.ingestion_progress", (0, 0, 1, 1, 0)),
        "citation_panel": _stable_id(pattern_slug, "component.citation_panel", (0, 0, 2, 0)),
        "explain_mode": _stable_id(pattern_slug, "component.explain_mode", (0, 0, 2, 1)),
        "action_document_select": _stable_action_id(pattern_slug, "document_select"),
        "action_chat_send": _stable_action_id(pattern_slug, "chat_send"),
        "action_citation_open": _stable_action_id(pattern_slug, "citation_open"),
        "action_ingestion_retry": _stable_action_id(pattern_slug, "ingestion_retry"),
    }


def _stable_id(pattern_slug: str, kind: str, path: tuple[int, ...]) -> str:
    encoded_path = ".".join(str(part) for part in path)
    payload = f"{pattern_slug}|{kind}|{encoded_path}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    safe_kind = kind.replace(".", "_")
    return f"pattern.{pattern_slug}.{safe_kind}.{digest}"


def _stable_action_id(pattern_slug: str, name: str) -> str:
    payload = f"{pattern_slug}|action|{name}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]
    return f"pattern.{pattern_slug}.action.{name}.{digest}"


def _ensure_rag_capability(capabilities: set[str], *, studio_mode: bool) -> None:
    if studio_mode:
        return
    if RAG_PATTERNS_CAPABILITY in capabilities:
        return
    raise Namel3ssError(
        f'RAG pattern components require capability "{RAG_PATTERNS_CAPABILITY}" or Studio mode.'
    )


def _validate_state_paths(config: RagChatPatternConfig) -> None:
    for path in (
        config.document_state_path,
        config.selected_document_state_path,
        config.message_state_path,
        config.streaming_state_path,
        config.citation_state_path,
        config.selected_citation_state_path,
        config.ingestion_status_state_path,
        config.explain_entries_state_path,
    ):
        if _STATE_PATH_RE.fullmatch(path):
            continue
        raise Namel3ssError(f'Invalid state path "{path}" in rag_chat pattern configuration.')


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    result = cleaned.strip("_")
    return result or "rag_chat"


__all__ = [
    "RAG_PATTERNS_CAPABILITY",
    "RagChatPatternConfig",
    "build_rag_chat_pattern",
    "validate_rag_chat_pattern",
]
