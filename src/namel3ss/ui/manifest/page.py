from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from copy import deepcopy

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.identity.guards import build_guard_context, enforce_requires
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.storage.metadata import PersistenceMetadata
from namel3ss.runtime.theme.resolution import ThemeSource, resolve_effective_theme
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.actions import _wire_overlay_actions
from namel3ss.ui.manifest.canonical import _slugify
from namel3ss.ui.manifest.elements import _build_children
from namel3ss.ui.manifest.state_defaults import StateContext, StateDefaults
from namel3ss.validation import ValidationMode


def build_manifest(
    program: ir.Program,
    *,
    state: dict | None = None,
    store: Storage | None = None,
    runtime_theme: str | None = None,
    persisted_theme: str | None = None,
    identity: dict | None = None,
    mode: ValidationMode | str = ValidationMode.RUNTIME,
    warnings: list | None = None,
    state_defaults: dict | None = None,
) -> dict:
    mode = ValidationMode.from_value(mode)
    ui_schema_version = "1"
    record_map: Dict[str, schema.RecordSchema] = {rec.name: rec for rec in program.records}
    pages = []
    actions: Dict[str, dict] = {}
    taken_actions: set[str] = set()
    state_base = deepcopy(state or {})
    theme_setting = getattr(program, "theme", "system")
    theme_current = runtime_theme or theme_setting
    effective = resolve_effective_theme(theme_current, False, None)
    source = ThemeSource.APP.value
    if persisted_theme and persisted_theme == theme_current:
        source = ThemeSource.PERSISTED.value
    elif runtime_theme and runtime_theme != theme_setting:
        source = ThemeSource.SESSION.value
    identity = identity or {}
    app_defaults = state_defaults or getattr(program, "state_defaults", None) or {}
    manifest_state_defaults_pages: dict[str, dict] = {}
    store_for_build = store if (mode == ValidationMode.RUNTIME or store is not None) else None
    for page in program.pages:
        page_defaults_raw = getattr(page, "state_defaults", None)
        defaults = StateDefaults(app_defaults, page_defaults_raw)
        state_ctx = StateContext(deepcopy(state_base), defaults)
        enforce_requires(
            build_guard_context(identity=identity, state=state_ctx.state),
            getattr(page, "requires", None),
            subject=f'page "{page.name}"',
            line=page.line,
            column=page.column,
            mode=mode,
            warnings=warnings,
        )
        page_slug = _slugify(page.name)
        elements, action_entries = _build_children(
            page.items,
            record_map,
            page.name,
            page_slug,
            [],
            store_for_build,
            identity,
            state_ctx,
            mode,
            warnings,
            taken_actions,
        )
        _wire_overlay_actions(elements, action_entries)
        for action_id, action_entry in action_entries.items():
            if action_id in actions:
                raise Namel3ssError(
                    f"Duplicate action id '{action_id}'. Use a unique id or omit to auto-generate.",
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
        defaults_snapshot = state_ctx.defaults_snapshot()
        if defaults_snapshot:
            manifest_state_defaults_pages[page_slug] = defaults_snapshot
    persistence = _resolve_persistence(store)
    if actions:
        actions = {action_id: actions[action_id] for action_id in sorted(actions)}
    manifest = {
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
    if app_defaults or manifest_state_defaults_pages:
        manifest["state_defaults"] = {"app": deepcopy(app_defaults) if app_defaults else {}, "pages": manifest_state_defaults_pages}
    return manifest


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


__all__ = ["build_manifest", "_build_children", "_wire_overlay_actions", "_slugify"]
