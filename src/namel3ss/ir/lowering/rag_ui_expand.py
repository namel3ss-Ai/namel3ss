from __future__ import annotations

from dataclasses import dataclass, replace

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.capabilities import has_ui_theming_capability

_DEFAULT_DRAWER_OPEN_PATH = ["ui", "show_drawer"]
_DEFAULT_UPLOAD_NAME = "intake"
_DEFAULT_ON_SEND_FLOW = "ask_question"
_DEFAULT_MESSAGES_PATH = ["chat", "messages"]
_DEFAULT_CITATIONS_PATH = ["chat", "citations"]
_DEFAULT_SCOPE_OPTIONS_PATH = ["chat", "scope_options"]
_DEFAULT_SCOPE_ACTIVE_PATH = ["chat", "scope_active"]
_DEFAULT_SOURCES_PATH = ["chat", "citations"]


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
    binds = _resolve_default_binds(
        rag,
        rag.bindings or ast.RagUIBindings(line=rag.line, column=rag.column),
        feature_set=feature_set,
    )
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


def _resolve_default_binds(
    rag: ast.RagUIBlock,
    binds: ast.RagUIBindings,
    *,
    feature_set: set[str],
) -> ast.RagUIBindings:
    resolved = binds
    if "conversation" in feature_set:
        if not resolved.on_send:
            resolved = replace(resolved, on_send=_DEFAULT_ON_SEND_FLOW)
        if resolved.messages is None:
            resolved = replace(resolved, messages=_state_path(rag, _DEFAULT_MESSAGES_PATH))
    if "evidence" in feature_set and resolved.citations is None:
        resolved = replace(resolved, citations=_state_path(rag, _DEFAULT_CITATIONS_PATH))
    if "research_tools" in feature_set:
        if resolved.scope_options is None:
            resolved = replace(resolved, scope_options=_state_path(rag, _DEFAULT_SCOPE_OPTIONS_PATH))
        if resolved.scope_active is None:
            resolved = replace(resolved, scope_active=_state_path(rag, _DEFAULT_SCOPE_ACTIVE_PATH))
    return resolved


def _state_path(rag: ast.RagUIBlock, path: list[str]) -> ast.StatePath:
    return ast.StatePath(path=list(path), line=rag.line, column=rag.column)


def _default_sidebar_items(
    rag: ast.RagUIBlock,
    binds: ast.RagUIBindings,
    feature_set: set[str],
) -> list[ast.PageItem]:
    items: list[ast.PageItem] = []
    if binds.threads is not None and binds.active_thread is not None:
        items.append(
            _shell_scope_section(
                rag,
                label="Threads",
                options_source=binds.threads,
                active_source=binds.active_thread,
                binding="threads",
                selection="single",
            )
        )
    if binds.models is not None and binds.active_models is not None:
        items.append(
            _shell_scope_section(
                rag,
                label="Models",
                options_source=binds.models,
                active_source=binds.active_models,
                binding="models",
                selection="multi",
            )
        )
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
    upload_name = _resolve_upload_name(binds.upload)
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
    items: list[ast.PageItem] = []
    if binds.suggestions is not None:
        suggestions = _suggestions_list_item(rag, binds.suggestions)
        _set_rag_binding_origin(suggestions, rag, binding="suggestions")
        items.append(ast.SectionItem(label="Suggestions", children=[suggestions], line=rag.line, column=rag.column))
    if "conversation" not in feature_set:
        return items
    chat_children: list[ast.PageItem] = [
        ast.ChatMessagesItem(source=binds.messages, line=rag.line, column=rag.column) if binds.messages else None,
    ]
    if binds.thinking is not None:
        chat_children.append(ast.ChatThinkingItem(when=binds.thinking, line=rag.line, column=rag.column))
    if "evidence" in feature_set and binds.citations is not None:
        chat_children.append(ast.ChatCitationsItem(source=binds.citations, line=rag.line, column=rag.column))
    chat_children = [child for child in chat_children if child is not None]
    if not chat_children:
        return items
    chat = ast.ChatItem(children=chat_children, streaming=True, line=rag.line, column=rag.column)
    items.append(ast.SectionItem(label="Chat", children=[chat], line=rag.line, column=rag.column))
    return items


def _shell_scope_section(
    rag: ast.RagUIBlock,
    *,
    label: str,
    options_source: ast.StatePath,
    active_source: ast.StatePath,
    binding: str,
    selection: str,
) -> ast.SectionItem:
    selector = ast.ScopeSelectorItem(
        options_source=options_source,
        active=active_source,
        line=rag.line,
        column=rag.column,
    )
    _set_rag_binding_origin(selector, rag, binding=binding, selection=selection)
    return ast.SectionItem(label=label, children=[selector], line=rag.line, column=rag.column)


def _suggestions_list_item(rag: ast.RagUIBlock, source: ast.StatePath) -> ast.ListItem:
    mapping = ast.ListItemMapping(primary="title", secondary="prompt", line=rag.line, column=rag.column)
    return ast.ListItem(
        source=source,
        item=mapping,
        empty_text="No suggestions yet.",
        line=rag.line,
        column=rag.column,
    )


def _set_rag_binding_origin(
    item: ast.PageItem,
    rag: ast.RagUIBlock,
    *,
    binding: str,
    selection: str | None = None,
    state_path: list[str] | None = None,
) -> None:
    origin = dict(getattr(item, "origin", {}) or {})
    rag_origin = dict(origin.get("rag_ui", {}) or {})
    rag_origin["base"] = rag.base
    rag_origin["features"] = list(getattr(rag, "features", []) or [])
    rag_origin["binding"] = binding
    if selection:
        rag_origin["selection"] = selection
    if state_path:
        rag_origin["state_path"] = list(state_path)
    origin["rag_ui"] = rag_origin
    setattr(item, "origin", origin)


def _default_composer_items(
    rag: ast.RagUIBlock,
    binds: ast.RagUIBindings,
    feature_set: set[str],
) -> list[ast.PageItem]:
    if "conversation" not in feature_set or not binds.on_send:
        return []
    composer = ast.ChatComposerItem(flow_name=binds.on_send, fields=[], line=rag.line, column=rag.column)
    if binds.composer_state is not None:
        _set_rag_binding_origin(
            composer,
            rag,
            binding="composer_state",
            state_path=binds.composer_state.path,
        )
    attachments_enabled = "research_tools" in feature_set
    composer_attach_upload = _resolve_upload_name(binds.upload) if attachments_enabled else None
    chat = ast.ChatItem(
        children=[composer],
        attachments=attachments_enabled,
        composer_attach_upload=composer_attach_upload,
        line=rag.line,
        column=rag.column,
    )
    return [chat]


def _resolve_upload_name(upload_name: str | None) -> str:
    normalized = str(upload_name or "").strip()
    return normalized or _DEFAULT_UPLOAD_NAME


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
    rag_origin = dict(origin.get("rag_ui", {}) or {})
    rag_origin["base"] = rag.base
    rag_origin["features"] = list(getattr(rag, "features", []) or [])
    rag_origin["region"] = region
    if slot:
        rag_origin["slot"] = slot
    origin["rag_ui"] = rag_origin
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
