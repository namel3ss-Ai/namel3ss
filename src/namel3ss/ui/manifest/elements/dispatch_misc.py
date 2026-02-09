from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.ui.manifest.theme_nodes import build_theme_settings_page
from namel3ss.validation import ValidationMode

from . import numbers as numbers_mod
from . import story as story_mod
from .custom_component import build_custom_component_element


def dispatch_misc_item(
    item: ir.PageItem,
    record_map: Dict[str, schema.RecordSchema],
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    media_registry: dict[str, Path],
    media_mode: MediaValidationMode,
    warnings: list | None,
    taken_actions: set[str],
    build_children,
    parent_visible: bool,
) -> tuple[dict, Dict[str, dict]] | None:
    if isinstance(item, ir.NumberItem):
        return numbers_mod.build_number_item(item, page_name=page_name, page_slug=page_slug, path=path)
    if isinstance(item, ir.StoryItem):
        return story_mod.build_story_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
        )
    if isinstance(item, ir.CustomComponentItem):
        return build_custom_component_element(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
        )
    if isinstance(item, ir.ThemeSettingsPageItem):
        return build_theme_settings_page(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
        )
    return None


__all__ = ["dispatch_misc_item"]
