from __future__ import annotations

from dataclasses import dataclass, field

from namel3ss.ast.base import Node
from namel3ss.ast.expressions import Literal, StatePath
from namel3ss.ast.pages import PageItem
from namel3ss.ast.ui_theme import ThemeTokens


@dataclass
class RagUIBindings(Node):
    messages: StatePath | None = None
    on_send: str | None = None
    citations: StatePath | None = None
    thinking: StatePath | None = None
    drawer_open: StatePath | None = None
    source_preview: StatePath | Literal | None = None
    sources: StatePath | None = None
    upload: str | None = None
    ingest_flow: str | None = None
    scope_options: StatePath | None = None
    scope_active: StatePath | None = None
    trust: StatePath | None = None
    toggle_sources_flow: str | None = None
    toggle_drawer_flow: str | None = None
    toggle_settings_flow: str | None = None


@dataclass
class RagUIBlock(PageItem):
    base: str | None = None
    features: list[str] = field(default_factory=list)
    bindings: RagUIBindings | None = None
    slots: dict[str, list[PageItem]] = field(default_factory=dict)
    theme_overrides: ThemeTokens | None = None


__all__ = ["RagUIBindings", "RagUIBlock"]
