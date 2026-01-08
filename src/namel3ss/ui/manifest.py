from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from namel3ss.ir import nodes as ir
from namel3ss.runtime.identity.guards import build_guard_context, enforce_requires
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.storage.metadata import PersistenceMetadata
from namel3ss.runtime.theme.resolution import ThemeSource, resolve_effective_theme
from namel3ss.schema import records as schema
from namel3ss.ui.manifest_page import _build_children, _slugify, _wire_overlay_actions


def build_manifest(
    program: ir.Program,
    *,
    state: dict | None = None,
    store: Storage | None = None,
    runtime_theme: str | None = None,
    persisted_theme: str | None = None,
    identity: dict | None = None,
) -> dict:
    ui_schema_version = "1"
    record_map: Dict[str, schema.RecordSchema] = {rec.name: rec for rec in program.records}
    pages = []
    actions: Dict[str, dict] = {}
    state = state or {}
    theme_setting = getattr(program, "theme", "system")
    theme_current = runtime_theme or theme_setting
    effective = resolve_effective_theme(theme_current, False, None)
    source = ThemeSource.APP.value
    if persisted_theme and persisted_theme == theme_current:
        source = ThemeSource.PERSISTED.value
    elif runtime_theme and runtime_theme != theme_setting:
        source = ThemeSource.SESSION.value
    identity = identity or {}
    for page in program.pages:
        enforce_requires(
            build_guard_context(identity=identity, state=state),
            getattr(page, "requires", None),
            subject=f'page "{page.name}"',
            line=page.line,
            column=page.column,
        )
        page_slug = _slugify(page.name)
        elements, action_entries = _build_children(
            page.items,
            record_map,
            page.name,
            page_slug,
            [],
            store,
            identity,
            state,
        )
        _wire_overlay_actions(elements, action_entries)
        for action_id, action_entry in action_entries.items():
            if action_id in actions:
                raise Namel3ssError(
                    f"UI action id '{action_id}' is duplicated on page '{page.name}'.",
                    line=page.line,
                    column=page.column,
                )
            actions[action_id] = action_entry
        pages.append(
            {
                "name": page.name,
                "slug": page_slug,
                "elements": elements,
            }
        )
    persistence = _resolve_persistence(store)
    if actions:
        actions = {action_id: actions[action_id] for action_id in sorted(actions)}
    return {
        "pages": pages,
        "actions": actions,
        "theme": {
            "schema_version": ui_schema_version,
            "setting": theme_setting,
            "current": theme_current,
            "persisted_current": persisted_theme,
            "effective": effective.value,
            "source": source,
            "runtime_supported": getattr(program, "theme_runtime_supported", False),
            "tokens": getattr(program, "theme_tokens", {}),
            "preference": getattr(program, "theme_preference", {"allow_override": False, "persist": "none"}),
        },
        "ui": {
            "persistence": persistence,
        },
    }


def _resolve_persistence(store: Storage | None) -> dict:
    default_meta = PersistenceMetadata(enabled=False, kind="memory", path=None, schema_version=None)
    if store is None:
        meta = default_meta
    else:
        getter = getattr(store, "get_metadata", None)
        meta = getter() if callable(getter) else default_meta
        meta = meta or default_meta
    if isinstance(meta, PersistenceMetadata):
        return asdict(meta)
    if isinstance(meta, dict):
        return {
            "enabled": bool(meta.get("enabled", False)),
            "kind": meta.get("kind") or "memory",
            "path": meta.get("path"),
            "schema_version": meta.get("schema_version"),
        }
    return asdict(default_meta)


__all__ = ["build_manifest"]
