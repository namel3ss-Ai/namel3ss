from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Iterable, Mapping

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.patterns.rag_chat import RAG_PATTERNS_CAPABILITY


_STATE_PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")


@dataclass(frozen=True)
class IngestionDashboardPatternConfig:
    name: str = "ingestion_dashboard"
    title: str = "Ingestion Dashboard"
    documents_state_path: str = "ingestionState.documents"
    selected_document_state_path: str = "ingestionState.selectedDocumentId"
    status_state_path: str = "ingestionState.status"
    errors_state_path: str = "ingestionState.errors"


def build_ingestion_dashboard_pattern(
    config: IngestionDashboardPatternConfig | None = None,
    *,
    capabilities: Iterable[str] | None = None,
    studio_mode: bool = False,
) -> dict[str, object]:
    resolved = config or IngestionDashboardPatternConfig()
    _validate_state_paths(resolved)
    capability_set = {str(item).strip().lower() for item in capabilities or []}
    if not studio_mode and RAG_PATTERNS_CAPABILITY not in capability_set:
        raise Namel3ssError(
            f'Ingestion dashboard components require capability "{RAG_PATTERNS_CAPABILITY}" or Studio mode.'
        )
    slug = _slugify(resolved.name)
    ids = _pattern_ids(slug)

    fragment = {
        "pattern": "ingestion_dashboard",
        "capability": RAG_PATTERNS_CAPABILITY,
        "name": resolved.name,
        "title": resolved.title,
        "state": [
            {"path": resolved.documents_state_path, "default": []},
            {"path": resolved.selected_document_state_path, "default": None},
            {"path": resolved.status_state_path, "default": {"status": "idle", "percent": 0}},
            {"path": resolved.errors_state_path, "default": []},
        ],
        "layout": [
            {
                "type": "layout.main",
                "id": ids["main"],
                "bindings": {"on_click": None, "keyboard_shortcut": None, "selected_item": None},
                "children": [
                    {
                        "type": "layout.two_pane",
                        "id": ids["two_pane"],
                        "bindings": {"on_click": None, "keyboard_shortcut": None, "selected_item": None},
                        "primary": [
                            {
                                "type": "component.document_library",
                                "id": ids["document_library"],
                                "title": "Uploads",
                                "documents_state": resolved.documents_state_path,
                                "selected_document_state": resolved.selected_document_state_path,
                                "bindings": {
                                    "on_click": ids["action_select_document"],
                                    "keyboard_shortcut": None,
                                    "selected_item": resolved.selected_document_state_path,
                                },
                                "line": 0,
                                "column": 0,
                            }
                        ],
                        "secondary": [
                            {
                                "type": "component.ingestion_progress",
                                "id": ids["ingestion_progress"],
                                "status_state": resolved.status_state_path,
                                "errors_state": resolved.errors_state_path,
                                "bindings": {
                                    "on_click": ids["action_retry_ingestion"],
                                    "keyboard_shortcut": None,
                                    "selected_item": None,
                                },
                                "line": 0,
                                "column": 0,
                            }
                        ],
                        "line": 0,
                        "column": 0,
                    }
                ],
                "line": 0,
                "column": 0,
            }
        ],
        "actions": {
            ids["action_select_document"]: {
                "id": ids["action_select_document"],
                "type": "component.document.select",
                "target": resolved.selected_document_state_path,
                "payload": {"documents_state": resolved.documents_state_path},
                "order": 0,
                "line": 0,
                "column": 0,
            },
            ids["action_retry_ingestion"]: {
                "id": ids["action_retry_ingestion"],
                "type": "component.ingestion.retry",
                "target": resolved.status_state_path,
                "payload": {"errors_state": resolved.errors_state_path},
                "order": 1,
                "line": 0,
                "column": 0,
            },
        },
    }
    validate_ingestion_dashboard_pattern(fragment)
    return fragment


def validate_ingestion_dashboard_pattern(fragment: Mapping[str, object]) -> None:
    layout = fragment.get("layout")
    if not isinstance(layout, list):
        raise Namel3ssError('ingestion_dashboard pattern must provide "layout" as a list.')

    found_primary_library = False
    found_secondary_progress = False

    for root in layout:
        if not isinstance(root, Mapping):
            continue
        if root.get("type") != "layout.main":
            continue
        children = root.get("children")
        if not isinstance(children, list):
            continue
        for child in children:
            if not isinstance(child, Mapping):
                continue
            if child.get("type") != "layout.two_pane":
                continue
            primary = child.get("primary")
            secondary = child.get("secondary")
            if isinstance(primary, list):
                found_primary_library = any(
                    isinstance(entry, Mapping) and entry.get("type") == "component.document_library"
                    for entry in primary
                )
            if isinstance(secondary, list):
                found_secondary_progress = any(
                    isinstance(entry, Mapping) and entry.get("type") == "component.ingestion_progress"
                    for entry in secondary
                )
    if not found_primary_library:
        raise Namel3ssError(
            "ingestion_dashboard pattern requires component.document_library in the primary pane."
        )
    if not found_secondary_progress:
        raise Namel3ssError(
            "ingestion_dashboard pattern requires component.ingestion_progress in the secondary pane."
        )


def _pattern_ids(pattern_slug: str) -> dict[str, str]:
    return {
        "main": _stable_id(pattern_slug, "layout.main", (0,)),
        "two_pane": _stable_id(pattern_slug, "layout.two_pane", (0, 0)),
        "document_library": _stable_id(pattern_slug, "component.document_library", (0, 0, 0)),
        "ingestion_progress": _stable_id(pattern_slug, "component.ingestion_progress", (0, 0, 1)),
        "action_select_document": _stable_action_id(pattern_slug, "select_document"),
        "action_retry_ingestion": _stable_action_id(pattern_slug, "retry_ingestion"),
    }


def _stable_id(pattern_slug: str, kind: str, path: tuple[int, ...]) -> str:
    payload = f"{pattern_slug}|{kind}|{'.'.join(str(entry) for entry in path)}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"pattern.{pattern_slug}.{kind.replace('.', '_')}.{digest}"


def _stable_action_id(pattern_slug: str, name: str) -> str:
    payload = f"{pattern_slug}|action|{name}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]
    return f"pattern.{pattern_slug}.action.{name}.{digest}"


def _validate_state_paths(config: IngestionDashboardPatternConfig) -> None:
    for path in (
        config.documents_state_path,
        config.selected_document_state_path,
        config.status_state_path,
        config.errors_state_path,
    ):
        if _STATE_PATH_RE.fullmatch(path):
            continue
        raise Namel3ssError(f'Invalid state path "{path}" in ingestion_dashboard pattern configuration.')


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    result = cleaned.strip("_")
    return result or "ingestion_dashboard"


__all__ = [
    "IngestionDashboardPatternConfig",
    "build_ingestion_dashboard_pattern",
    "validate_ingestion_dashboard_pattern",
]
