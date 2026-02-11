from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode

from . import polish as polish_mod


def dispatch_polish_item(
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
    if isinstance(item, ir.LoadingItem):
        return polish_mod.build_loading_item(item, page_name=page_name, page_slug=page_slug, path=path)
    if isinstance(item, ir.BadgeItem):
        return polish_mod.build_badge_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
        )
    if isinstance(item, ir.SnackbarItem):
        return polish_mod.build_snackbar_item(item, page_name=page_name, page_slug=page_slug, path=path)
    if isinstance(item, ir.IconItem):
        return polish_mod.build_icon_item(item, page_name=page_name, page_slug=page_slug, path=path)
    if isinstance(item, ir.LightboxItem):
        return polish_mod.build_lightbox_item(item, page_name=page_name, page_slug=page_slug, path=path)
    if isinstance(item, ir.GridItem):
        return polish_mod.build_grid_item(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            store=store,
            identity=identity,
            state_ctx=state_ctx,
            mode=mode,
            media_registry=media_registry,
            media_mode=media_mode,
            warnings=warnings,
            taken_actions=taken_actions,
            build_children=build_children,
            parent_visible=parent_visible,
        )
    return None


__all__ = ["dispatch_polish_item"]
