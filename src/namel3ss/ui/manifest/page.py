from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from copy import deepcopy

from namel3ss.agents.intent import build_agent_team_intent
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.foreign.intent import build_foreign_functions_intent
from namel3ss.foreign.policy import foreign_policy_mode
from namel3ss.ir import nodes as ir
from namel3ss.page_layout import PAGE_LAYOUT_SLOT_ORDER
from namel3ss.flow_contract import validate_declarative_flows
from namel3ss.media import MediaValidationMode, media_registry, media_root_for_program
from namel3ss.runtime.identity.guards import build_guard_context, enforce_requires
from namel3ss.runtime.mutation_policy import append_mutation_policy_warnings
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.storage.metadata import PersistenceMetadata
from namel3ss.runtime.theme.resolution import ThemeSource, resolve_effective_theme
from namel3ss.schema import records as schema
from namel3ss.schema.evolution import (
    append_schema_evolution_warnings,
    enforce_runtime_schema_compatibility,
)
from namel3ss.ui.manifest.actions import (
    _allocate_action_id,
    _ingestion_review_action_id,
    _ingestion_skip_action_id,
    _retrieval_action_id,
    _upload_replace_action_id,
    _wire_overlay_actions,
)
from namel3ss.ui.manifest.canonical import _slugify
from namel3ss.ui.manifest.accessibility import apply_accessibility_contract
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO
from namel3ss.ui.manifest.elements import _build_children
from namel3ss.ui.manifest.filter_mode import apply_display_mode_filter
from namel3ss.ui.manifest.navigation import select_active_page
from namel3ss.ui.manifest.plugin_assets import build_plugin_assets_manifest
from namel3ss.ui.manifest.upload_analysis import (
    collect_upload_reference_names,
    collect_upload_requests,
)
from namel3ss.ui.manifest.upload_manifest import inject_default_upload_control, public_upload_request
from namel3ss.ui.manifest.state_defaults import StateContext, StateDefaults
from namel3ss.ui.manifest.status import select_status_items
from namel3ss.ui.manifest.visibility import evaluate_visibility
from namel3ss.ui.manifest.warning_pipeline import append_manifest_warnings
from namel3ss.ui.responsive import apply_responsive_layout_to_pages
from namel3ss.ui.spacing import apply_spacing_to_pages
from namel3ss.ui.settings import UI_DEFAULTS, UI_RUNTIME_THEME_VALUES, normalize_ui_settings, validate_ui_contrast
from namel3ss.validation import ValidationMode


def build_manifest(
    program: ir.Program,
    *,
    config: AppConfig | None = None,
    state: dict | None = None,
    store: Storage | None = None,
    runtime_theme: str | None = None,
    persisted_theme: str | None = None,
    identity: dict | None = None,
    auth_context: object | None = None,
    mode: ValidationMode | str = ValidationMode.RUNTIME,
    warnings: list | None = None,
    state_defaults: dict | None = None,
    media_mode: MediaValidationMode | str | None = None,
    display_mode: str = DISPLAY_MODE_STUDIO,
    diagnostics_enabled: bool = False,
) -> dict:
    mode = ValidationMode.from_value(mode)
    media_mode = MediaValidationMode.from_value(media_mode)
    ui_schema_version = "1"
    record_map: Dict[str, schema.RecordSchema] = {rec.name: rec for rec in program.records}
    if mode == ValidationMode.RUNTIME:
        enforce_runtime_schema_compatibility(
            record_map.values(),
            project_root=getattr(program, "project_root", None),
            store=store,
        )
    if mode == ValidationMode.STATIC:
        append_schema_evolution_warnings(program, warnings)
    validate_declarative_flows(
        list(getattr(program, "flows", [])),
        record_map,
        getattr(program, "tools", None),
        mode=mode,
        warnings=warnings,
    )
    append_mutation_policy_warnings(program, warnings=warnings, mode=mode)
    media_root = media_root_for_program(program)
    media_index = media_registry(root=media_root)
    pages = []
    actions: Dict[str, dict] = {}
    taken_actions: set[str] = set()
    state_base = deepcopy(state or {})
    raw_ui_settings = getattr(program, "ui_settings", None)
    ui_settings = normalize_ui_settings(raw_ui_settings)
    theme_setting = getattr(program, "theme", UI_DEFAULTS["theme"])
    allowed_themes = set(UI_RUNTIME_THEME_VALUES)
    theme_current = runtime_theme if runtime_theme in allowed_themes else theme_setting
    persisted_theme_normalized = persisted_theme if persisted_theme in allowed_themes else None
    effective = resolve_effective_theme(theme_current, False, None)
    source = ThemeSource.APP.value
    if persisted_theme_normalized and persisted_theme_normalized == theme_current:
        source = ThemeSource.PERSISTED.value
    elif runtime_theme and runtime_theme in allowed_themes and runtime_theme != theme_setting:
        source = ThemeSource.SESSION.value
    identity = identity or {}
    app_defaults = state_defaults or getattr(program, "state_defaults", None) or {}
    manifest_state_defaults_pages: dict[str, dict] = {}
    ui_plugin_registry = getattr(program, "ui_plugin_registry", None)
    responsive_layout = getattr(program, "responsive_layout", None)
    breakpoint_names = tuple(getattr(getattr(responsive_layout, "breakpoints", None), "names", ()) or ())
    breakpoint_values = tuple(getattr(getattr(responsive_layout, "breakpoints", None), "values", ()) or ())
    capabilities = tuple(getattr(program, "capabilities", ()) or ())
    diagnostics_enabled = bool(diagnostics_enabled or display_mode == DISPLAY_MODE_STUDIO)
    upload_requests_with_location = collect_upload_requests(program)
    upload_requests = [public_upload_request(entry) for entry in upload_requests_with_location]
    upload_reference_names = tuple(sorted(collect_upload_reference_names(program)))
    store_for_build = store if (mode == ValidationMode.RUNTIME or store is not None) else None
    for page in program.pages:
        page_defaults_raw = getattr(page, "state_defaults", None)
        defaults = StateDefaults(app_defaults, page_defaults_raw)
        state_ctx = StateContext(deepcopy(state_base), defaults)
        setattr(state_ctx, "ui_plugin_registry", ui_plugin_registry)
        setattr(state_ctx, "theme_tokens", getattr(program, "theme_tokens", {}) or {})
        page_visible, _ = evaluate_visibility(
            getattr(page, "visibility", None),
            getattr(page, "visibility_rule", None),
            state_ctx,
            mode,
            warnings,
            line=getattr(page, "line", None),
            column=getattr(page, "column", None),
        )
        if not page_visible:
            continue
        enforce_requires(
            build_guard_context(identity=identity, state=state_ctx.state, auth_context=auth_context),
            getattr(page, "requires", None),
            subject=f'page "{page.name}"',
            line=page.line,
            column=page.column,
            mode=mode,
            warnings=warnings,
        )
        page_slug = _slugify(page.name)
        page_layout = getattr(page, "layout", None)
        page_is_diagnostics = bool(getattr(page, "diagnostics", False))
        status_items = select_status_items(
            getattr(page, "status", None),
            state_ctx,
            mode,
            warnings,
            line=page.line,
            column=page.column,
        )
        action_entries: Dict[str, dict] = {}
        page_payload: dict
        if status_items is not None or page_layout is None:
            items = status_items if status_items is not None else page.items
            elements, action_entries = _build_children(
                items,
                record_map,
                page.name,
                page_slug,
                [],
                store_for_build,
                identity,
                state_ctx,
                mode,
                media_index,
                media_mode,
                warnings,
                taken_actions,
            )
            _wire_overlay_actions(elements, action_entries)
            page_payload = {
                "name": page.name,
                "slug": page_slug,
                "elements": elements,
            }
        else:
            layout_payload: dict[str, list[dict]] = {}
            top_level_layout_elements: list[dict] = []
            diagnostics_elements: list[dict] = []
            for slot_index, slot_name in enumerate(PAGE_LAYOUT_SLOT_ORDER):
                slot_items = getattr(page_layout, slot_name, None) or []
                slot_elements, slot_actions = _build_children(
                    slot_items,
                    record_map,
                    page.name,
                    page_slug,
                    [slot_index],
                    store_for_build,
                    identity,
                    state_ctx,
                    mode,
                    media_index,
                    media_mode,
                    warnings,
                    taken_actions,
                )
                layout_payload[slot_name] = slot_elements
                top_level_layout_elements.extend(slot_elements)
                action_entries.update(slot_actions)
            diagnostics_items = getattr(page_layout, "diagnostics", None) or []
            if diagnostics_items:
                diagnostics_elements, diagnostics_actions = _build_children(
                    diagnostics_items,
                    record_map,
                    page.name,
                    page_slug,
                    [len(PAGE_LAYOUT_SLOT_ORDER)],
                    store_for_build,
                    identity,
                    state_ctx,
                    mode,
                    media_index,
                    media_mode,
                    warnings,
                    taken_actions,
                )
                action_entries.update(diagnostics_actions)
                _wire_overlay_actions(diagnostics_elements, action_entries)
            _wire_overlay_actions(top_level_layout_elements, action_entries)
            page_payload = {
                "name": page.name,
                "slug": page_slug,
                "layout": layout_payload,
            }
            if diagnostics_elements:
                page_payload["diagnostics_blocks"] = diagnostics_elements
        for action_id, action_entry in action_entries.items():
            if action_id in actions:
                raise Namel3ssError(
                    f"Duplicate action id '{action_id}'. Use a unique id or omit to auto-generate.",
                    line=page.line,
                    column=page.column,
                )
            actions[action_id] = action_entry
        pages.append(page_payload)
        if page_is_diagnostics:
            pages[-1]["diagnostics"] = True
        page_debug_only = getattr(page, "debug_only", None)
        if page_debug_only is False:
            pages[-1]["debug_only"] = False
        elif isinstance(page_debug_only, str):
            pages[-1]["debug_only"] = page_debug_only
        elif page_debug_only:
            pages[-1]["debug_only"] = True
        if getattr(page, "purpose", None):
            pages[-1]["purpose"] = page.purpose
        defaults_snapshot = state_ctx.defaults_snapshot()
        if defaults_snapshot:
            manifest_state_defaults_pages[page_slug] = defaults_snapshot
    warning_context = {
        "capabilities": capabilities,
        "upload_requests": upload_requests_with_location,
        "upload_reference_names": upload_reference_names,
    }
    injected_upload = inject_default_upload_control(
        pages=pages,
        actions=actions,
        taken_actions=taken_actions,
        state=state_base,
        capabilities=capabilities,
        display_mode=display_mode,
    )
    if injected_upload:
        warning_context["studio_injected_upload"] = True
    navigation_state = StateContext(deepcopy(state_base), StateDefaults(app_defaults))
    navigation = select_active_page(
        getattr(program, "ui_active_page_rules", None),
        pages=pages,
        state_ctx=navigation_state,
    )
    apply_responsive_layout_to_pages(pages, breakpoint_names=breakpoint_names)
    apply_spacing_to_pages(pages, ui_settings.get("density", UI_DEFAULTS["density"]))
    validate_ui_contrast(theme_setting, ui_settings.get("accent_color", ""), raw_ui_settings)
    if theme_current != theme_setting:
        validate_ui_contrast(theme_current, ui_settings.get("accent_color", ""), None)
    apply_accessibility_contract(pages)
    append_manifest_warnings(pages, warnings, context=warning_context)
    if "uploads" in capabilities:
        _add_system_action(actions, taken_actions, _retrieval_action_id(), "retrieval_run")
        _add_system_action(actions, taken_actions, _ingestion_review_action_id(), "ingestion_review")
        _add_system_action(actions, taken_actions, _ingestion_skip_action_id(), "ingestion_skip")
        _add_system_action(actions, taken_actions, _upload_replace_action_id(), "upload_replace")
    persistence = _resolve_persistence(store)
    if actions:
        actions = {action_id: actions[action_id] for action_id in sorted(actions)}
    resolved_theme = getattr(program, "resolved_theme", None)
    theme_definition = getattr(resolved_theme, "definition", None)
    has_theme_definition = bool(
        theme_definition is not None
        and (
            theme_definition.preset
            or theme_definition.brand_palette
            or theme_definition.tokens
            or getattr(theme_definition, "responsive_tokens", None)
            or theme_definition.harmonize
            or theme_definition.allow_low_contrast
            or theme_definition.density
            or theme_definition.motion
            or theme_definition.shape
            or theme_definition.surface
        )
    )
    theme_preference = dict(getattr(program, "theme_preference", {"allow_override": False, "persist": "none"}) or {})
    if has_theme_definition:
        theme_preference.setdefault("storage_key", "namel3ss_theme")
    legacy_theme_tokens = dict(getattr(program, "theme_tokens", {}) or {})
    visual_theme_tokens = dict(getattr(program, "ui_visual_theme_tokens", {}) or {})
    merged_theme_tokens = dict(legacy_theme_tokens)
    merged_theme_tokens.update(visual_theme_tokens)
    visual_theme_name = str(getattr(program, "ui_visual_theme_name", "default") or "default")
    visual_theme_css = str(getattr(program, "ui_visual_theme_css", "") or "")
    visual_theme_css_hash = str(getattr(program, "ui_visual_theme_css_hash", "") or "")
    visual_theme_font_url = getattr(program, "ui_visual_theme_font_url", None)
    manifest = {
        "pages": pages,
        "actions": actions,
        "diagnostics_enabled": diagnostics_enabled,
        "theme": {
            "schema_version": ui_schema_version,
            "setting": theme_setting,
            "current": theme_current,
            "persisted_current": persisted_theme_normalized,
            "effective": effective.value,
            "source": source,
            "runtime_supported": getattr(program, "theme_runtime_supported", False),
            "theme_name": visual_theme_name,
            "tokens": merged_theme_tokens,
            "runtime_tokens": legacy_theme_tokens,
            "css": visual_theme_css,
            "css_hash": visual_theme_css_hash,
            "preference": theme_preference,
        },
        "ui": {
            "persistence": persistence,
            "settings": ui_settings,
        },
    }
    plugin_assets = build_plugin_assets_manifest(ui_plugin_registry)
    if plugin_assets:
        manifest["ui"]["plugins"] = plugin_assets
    if isinstance(visual_theme_font_url, str) and visual_theme_font_url:
        manifest["theme"]["font_url"] = visual_theme_font_url
    if upload_requests:
        manifest["upload_requests"] = upload_requests
    hook_manager = getattr(program, "extension_hook_manager", None)
    if display_mode == DISPLAY_MODE_STUDIO and hook_manager is not None:
        session_id = None
        if isinstance(identity, dict):
            candidate = identity.get("session_id")
            if isinstance(candidate, str) and candidate:
                session_id = candidate
        studio_panels = tuple(hook_manager.run_studio_hooks(session_id=session_id))
        if studio_panels:
            manifest.setdefault("studio", {})
            manifest["studio"]["extension_panels"] = list(studio_panels)
    responsive_theme_tokens = dict(getattr(program, "responsive_theme_tokens", {}) or {})
    if responsive_theme_tokens:
        manifest["theme"]["responsive_tokens"] = {
            key: list(value)
            for key, value in responsive_theme_tokens.items()
        }
    responsive_token_scales = dict(getattr(program, "responsive_theme_tokens", {}) or {})
    if responsive_layout is not None or responsive_token_scales:
        manifest["ui"]["responsive"] = {
            "enabled": bool(responsive_layout is not None),
            "breakpoints": [
                {"name": name, "width": int(width)}
                for name, width in zip(breakpoint_names, breakpoint_values)
            ],
            "columns": int(getattr(responsive_layout, "total_columns", 12) if responsive_layout is not None else 12),
            "token_scales": {key: list(value) for key, value in responsive_token_scales.items()},
        }
    if has_theme_definition:
        manifest["theme"]["definition"] = {
            "preset": theme_definition.preset,
            "brand_palette": dict(theme_definition.brand_palette),
            "tokens": dict(theme_definition.tokens),
            "responsive_tokens": {
                key: list(value)
                for key, value in dict(getattr(theme_definition, "responsive_tokens", {}) or {}).items()
            },
            "harmonize": bool(theme_definition.harmonize),
            "allow_low_contrast": bool(theme_definition.allow_low_contrast),
            "axes": {
                "density": theme_definition.density,
                "motion": theme_definition.motion,
                "shape": theme_definition.shape,
                "surface": theme_definition.surface,
            },
        }
    if navigation:
        manifest["navigation"] = navigation
    agent_team = build_agent_team_intent(program)
    if agent_team is not None:
        manifest["agent_team"] = agent_team
    foreign_intent = build_foreign_functions_intent(program, policy_mode=foreign_policy_mode(config))
    if foreign_intent:
        manifest["foreign_functions"] = foreign_intent
    if app_defaults or manifest_state_defaults_pages:
        manifest["state_defaults"] = {"app": deepcopy(app_defaults) if app_defaults else {}, "pages": manifest_state_defaults_pages}
    return apply_display_mode_filter(
        manifest,
        display_mode=display_mode,
        diagnostics_enabled=diagnostics_enabled,
    )


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


def _add_system_action(actions: Dict[str, dict], taken_actions: set[str], base_id: str, action_type: str) -> None:
    action_id = _allocate_action_id(base_id, f"system.{action_type}", taken_actions)
    if action_id in actions:
        return
    actions[action_id] = {"id": action_id, "type": action_type, "debug_only": True}
    taken_actions.add(action_id)


__all__ = ["build_manifest", "_build_children", "_wire_overlay_actions", "_slugify"]
