from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.capabilities import has_ui_theming_capability

_DEFAULT_DRAWER_OPEN_PATH = ["ui", "show_drawer"]
_DEFAULT_UPLOAD_NAME = "intake"
_DEFAULT_SOURCES_PATH = ["chat", "citations"]
_DEFAULT_THINKING_PATH = ["loading"]


@dataclass(frozen=True)
class RagUIExpansion:
    items: list[ast.PageItem]
    theme_overrides: ast.ThemeTokens | None
    used: bool


def expand_rag_ui_page(
    page: ast.PageDecl,
    *,
    capabilities: tuple[str, ...] | None = None,
) -> RagUIExpansion:
    rag_items = [item for item in page.items if isinstance(item, ast.RagUIBlock)]
    if not rag_items:
        return RagUIExpansion(items=page.items, theme_overrides=None, used=False)
    if len(rag_items) > 1:
        rag_item = rag_items[1]
        raise Namel3ssError(
            "rag_ui may only appear once per page.",
            line=getattr(rag_item, "line", None),
            column=getattr(rag_item, "column", None),
        )
    if len(page.items) != 1:
        rag_item = rag_items[0]
        raise Namel3ssError(
            "rag_ui must be the only page body entry.",
            line=getattr(rag_item, "line", None),
            column=getattr(rag_item, "column", None),
        )
    rag = rag_items[0]
    expanded = _expand_rag_ui_block(rag, page_name=page.name, capabilities=capabilities or ())
    return RagUIExpansion(items=expanded, theme_overrides=rag.theme_overrides, used=True)


def _expand_rag_ui_block(
    rag: ast.RagUIBlock,
    *,
    page_name: str,
    capabilities: tuple[str, ...],
) -> list[ast.PageItem]:
    features = tuple(getattr(rag, "features", []) or [])
    feature_set = set(features)
    binds = rag.bindings or ast.RagUIBindings(line=rag.line, column=rag.column)
    slots = dict(getattr(rag, "slots", {}) or {})
    header_items = slots.get("header")
    sidebar_items = slots.get("sidebar")
    chat_items = slots.get("chat")
    composer_items = slots.get("composer")
    drawer_items = slots.get("drawer")

    header = None
    if header_items is None:
        header_items = _default_header_items(rag, page_name, binds, feature_set, capabilities)
    if header_items:
        header_row = ast.LayoutRow(
            children=header_items,
            line=rag.line,
            column=rag.column,
        )
        header = ast.LayoutSticky(
            position="top",
            children=[header_row],
            line=rag.line,
            column=rag.column,
        )
        _tag_region(header, rag, region="header", slot="header" if "header" in slots else None, recurse=True)

    if sidebar_items is None:
        sidebar_items = _default_sidebar_items(rag, binds, feature_set)
    _tag_region_items(sidebar_items, rag, region="sidebar", slot="sidebar" if "sidebar" in slots else None)

    if chat_items is None:
        chat_items = _default_chat_items(rag, binds, feature_set)
    _tag_region_items(chat_items, rag, region="main", slot="chat" if "chat" in slots else None)

    if composer_items is None:
        composer_items = _default_composer_items(rag, binds, feature_set)
    _tag_region_items(composer_items, rag, region="composer", slot="composer" if "composer" in slots else None)

    composer = None
    if composer_items:
        composer = ast.LayoutSticky(
            position="bottom",
            children=composer_items,
            line=rag.line,
            column=rag.column,
        )
        _tag_region(composer, rag, region="composer", slot="composer" if "composer" in slots else None, recurse=True)

    drawer = None
    if drawer_items is None:
        drawer_items = _default_drawer_items(rag, binds, feature_set, capabilities)
    if drawer_items:
        drawer = ast.LayoutDrawer(
            title="Citations",
            children=drawer_items,
            show_when=_drawer_open_expr(rag, binds),
            line=rag.line,
            column=rag.column,
        )
        _tag_region(drawer, rag, region="drawer", slot="drawer" if "drawer" in slots else None, recurse=True)

    chat_column_children: list[ast.PageItem] = []
    if chat_items:
        chat_column_children.extend(chat_items)
    if composer is not None:
        chat_column_children.append(composer)
    chat_column = ast.LayoutColumn(children=chat_column_children, line=rag.line, column=rag.column)
    _tag_region(chat_column, rag, region="shell", slot=None, recurse=False)

    main_row_children: list[ast.PageItem] = [chat_column]
    if drawer is not None:
        main_row_children.append(drawer)

    main_row = ast.LayoutRow(children=main_row_children, line=rag.line, column=rag.column)
    _tag_region(main_row, rag, region="shell", slot=None, recurse=False)

    sidebar_layout = ast.SidebarLayout(
        sidebar=sidebar_items or [],
        main=[main_row],
        line=rag.line,
        column=rag.column,
    )
    _tag_region(sidebar_layout, rag, region="shell", slot=None, recurse=False)

    root_children: list[ast.PageItem] = []
    if header is not None:
        root_children.append(header)
    root_children.append(sidebar_layout)
    root = ast.LayoutStack(children=root_children, direction="vertical", line=rag.line, column=rag.column)
    _tag_region(root, rag, region="shell", slot=None, recurse=False)
    return [root]


def _default_header_items(
    rag: ast.RagUIBlock,
    page_name: str,
    binds: ast.RagUIBindings,
    feature_set: set[str],
    capabilities: tuple[str, ...],
) -> list[ast.PageItem]:
    items: list[ast.PageItem] = [
        ast.TitleItem(value=page_name, line=rag.line, column=rag.column),
    ]
    if "research_tools" in feature_set and binds.trust is not None:
        items.append(ast.TrustIndicatorItem(source=binds.trust, line=rag.line, column=rag.column))
    if binds.toggle_sources_flow:
        items.append(_flow_button("Sources", binds.toggle_sources_flow, rag))
    if binds.toggle_drawer_flow:
        items.append(_flow_button("Citations", binds.toggle_drawer_flow, rag))
    if binds.toggle_settings_flow and has_ui_theming_capability(capabilities):
        items.append(_flow_button("Settings", binds.toggle_settings_flow, rag))
    return items


def _default_sidebar_items(
    rag: ast.RagUIBlock,
    binds: ast.RagUIBindings,
    feature_set: set[str],
) -> list[ast.PageItem]:
    items: list[ast.PageItem] = []
    if "research_tools" in feature_set and binds.scope_options is not None and binds.scope_active is not None:
        items.append(
            ast.ScopeSelectorItem(
                options_source=binds.scope_options,
                active=binds.scope_active,
                line=rag.line,
                column=rag.column,
            )
        )
    section_children: list[ast.PageItem] = []
    upload_name = binds.upload or _DEFAULT_UPLOAD_NAME
    section_children.append(ast.UploadItem(name=upload_name, line=rag.line, column=rag.column))
    if binds.ingest_flow:
        section_children.append(_flow_button("Run ingestion", binds.ingest_flow, rag))
    sources = binds.sources or binds.citations or ast.StatePath(path=list(_DEFAULT_SOURCES_PATH), line=rag.line, column=rag.column)
    section_children.append(_sources_list_item(rag, sources))
    items.append(ast.SectionItem(label="Sources", children=section_children, line=rag.line, column=rag.column))
    return items


def _default_chat_items(
    rag: ast.RagUIBlock,
    binds: ast.RagUIBindings,
    feature_set: set[str],
) -> list[ast.PageItem]:
    if "conversation" not in feature_set:
        return []
    chat_children: list[ast.PageItem] = [
        ast.ChatMessagesItem(source=binds.messages, line=rag.line, column=rag.column) if binds.messages else None,
    ]
    if binds.thinking is not None:
        chat_children.append(ast.ChatThinkingItem(when=binds.thinking, line=rag.line, column=rag.column))
    if "evidence" in feature_set and binds.citations is not None:
        chat_children.append(ast.ChatCitationsItem(source=binds.citations, line=rag.line, column=rag.column))
    chat_children = [child for child in chat_children if child is not None]
    if not chat_children:
        return []
    chat = ast.ChatItem(children=chat_children, streaming=True, line=rag.line, column=rag.column)
    return [ast.SectionItem(label="Chat", children=[chat], line=rag.line, column=rag.column)]


def _default_composer_items(
    rag: ast.RagUIBlock,
    binds: ast.RagUIBindings,
    feature_set: set[str],
) -> list[ast.PageItem]:
    if "conversation" not in feature_set or not binds.on_send:
        return []
    composer = ast.ChatComposerItem(flow_name=binds.on_send, fields=[], line=rag.line, column=rag.column)
    chat = ast.ChatItem(children=[composer], line=rag.line, column=rag.column)
    return [chat]


def _default_drawer_items(
    rag: ast.RagUIBlock,
    binds: ast.RagUIBindings,
    feature_set: set[str],
    capabilities: tuple[str, ...],
) -> list[ast.PageItem]:
    if "evidence" not in feature_set:
        return []
    tabs: list[ast.TabItem] = []
    citations_source = binds.citations
    if citations_source is not None:
        citations_list = _sources_list_item(rag, citations_source)
        tabs.append(ast.TabItem(label="Citations", children=[citations_list], line=rag.line, column=rag.column))
    preview_items: list[ast.PageItem] = []
    if binds.source_preview is not None:
        preview_items.append(ast.SourcePreviewItem(source=binds.source_preview, line=rag.line, column=rag.column))
    else:
        preview_items.append(ast.TextItem(value="Select a citation to preview.", line=rag.line, column=rag.column))
    tabs.append(ast.TabItem(label="Preview", children=preview_items, line=rag.line, column=rag.column))
    explain_items = [ast.TextItem(value="Retrieval explain data appears after a run.", line=rag.line, column=rag.column)]
    tabs.append(ast.TabItem(label="Explain", children=explain_items, line=rag.line, column=rag.column))
    if has_ui_theming_capability(capabilities):
        tabs.append(
            ast.TabItem(
                label="Settings",
                children=[ast.ThemeSettingsPageItem(line=rag.line, column=rag.column)],
                line=rag.line,
                column=rag.column,
            )
        )
    if not tabs:
        return []
    return [ast.TabsItem(tabs=tabs, default="Citations", line=rag.line, column=rag.column)]


def _flow_button(label: str, flow_name: str, rag: ast.RagUIBlock) -> ast.ButtonItem:
    return ast.ButtonItem(label=label, flow_name=flow_name, line=rag.line, column=rag.column)


def _sources_list_item(rag: ast.RagUIBlock, source: ast.StatePath) -> ast.ListItem:
    mapping = ast.ListItemMapping(primary="title", secondary="snippet", meta="url", line=rag.line, column=rag.column)
    return ast.ListItem(
        source=source,
        item=mapping,
        empty_text="No sources yet.",
        line=rag.line,
        column=rag.column,
    )


def _drawer_open_expr(rag: ast.RagUIBlock, binds: ast.RagUIBindings) -> ast.StatePath:
    if binds.drawer_open is not None:
        return binds.drawer_open
    return ast.StatePath(path=list(_DEFAULT_DRAWER_OPEN_PATH), line=rag.line, column=rag.column)


def _tag_region_items(items: list[ast.PageItem], rag: ast.RagUIBlock, *, region: str, slot: str | None) -> None:
    for item in items:
        _tag_region(item, rag, region=region, slot=slot, recurse=True)


def _tag_region(item: ast.PageItem, rag: ast.RagUIBlock, *, region: str, slot: str | None, recurse: bool) -> None:
    origin = dict(getattr(item, "origin", {}) or {})
    origin["rag_ui"] = {
        "base": rag.base,
        "features": list(getattr(rag, "features", []) or []),
        "region": region,
    }
    if slot:
        origin["rag_ui"]["slot"] = slot
    setattr(item, "origin", origin)
    if recurse:
        _tag_children(item, rag, region=region, slot=slot)


def _tag_children(item: ast.PageItem, rag: ast.RagUIBlock, *, region: str, slot: str | None) -> None:
    children = getattr(item, "children", None)
    if isinstance(children, list):
        for child in children:
            _tag_region(child, rag, region=region, slot=slot, recurse=True)
    if isinstance(item, ast.SidebarLayout):
        for child in item.sidebar or []:
            _tag_region(child, rag, region="sidebar", slot=slot, recurse=True)
        for child in item.main or []:
            _tag_region(child, rag, region="main", slot=slot, recurse=True)
    if isinstance(item, ast.ConditionalBlock):
        for child in item.then_children:
            _tag_region(child, rag, region=region, slot=slot, recurse=True)
        for child in item.else_children or []:
            _tag_region(child, rag, region=region, slot=slot, recurse=True)
    tabs = getattr(item, "tabs", None)
    if isinstance(tabs, list):
        for tab in tabs:
            for child in tab.children:
                _tag_region(child, rag, region=region, slot=slot, recurse=True)


__all__ = ["RagUIExpansion", "expand_rag_ui_page"]
