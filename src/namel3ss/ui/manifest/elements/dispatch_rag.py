from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui import manifest_rag as rag_mod
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode


def dispatch_rag_item(
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
    if isinstance(item, ir.CitationChipsItem):
        return rag_mod.build_citation_chips_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
            mode=mode,
            warnings=warnings,
        )
    if isinstance(item, ir.SourcePreviewItem):
        return rag_mod.build_source_preview_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
        )
    if isinstance(item, ir.TrustIndicatorItem):
        return rag_mod.build_trust_indicator_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
        )
    if isinstance(item, ir.ScopeSelectorItem):
        return rag_mod.build_scope_selector_item(
            item,
            page_name=page_name,
            page_slug=page_slug,
            path=path,
            state_ctx=state_ctx,
        )
    return None


__all__ = ["dispatch_rag_item"]
