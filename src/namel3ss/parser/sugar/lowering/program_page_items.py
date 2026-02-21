from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar.lowering.expressions import _lower_expression


def _lower_page_item(item: ast.PageItem) -> ast.PageItem:
    if isinstance(item, ast.CardItem):
        children = [_lower_page_item(child) for child in item.children]
        stat = _lower_card_stat(item.stat)
        actions = _lower_card_actions(item.actions)
        lowered = ast.CardItem(
            label=item.label,
            children=children,
            stat=stat,
            actions=actions,
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_style_metadata(lowered, item)
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.CardGroupItem):
        children = [_lower_page_item(child) for child in item.children]
        lowered = ast.CardGroupItem(
            children=children,
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.ComposeItem):
        children = [_lower_page_item(child) for child in item.children]
        lowered = ast.ComposeItem(
            name=item.name,
            children=children,
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.RowItem):
        children = [_lower_page_item(child) for child in item.children]
        lowered = ast.RowItem(
            children=children,
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.ColumnItem):
        children = [_lower_page_item(child) for child in item.children]
        lowered = ast.ColumnItem(
            children=children,
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.GridItem):
        children = [_lower_page_item(child) for child in item.children]
        lowered = ast.GridItem(
            columns=list(getattr(item, "columns", []) or []),
            children=children,
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.SectionItem):
        children = [_lower_page_item(child) for child in item.children]
        lowered = ast.SectionItem(
            label=item.label,
            children=children,
            columns=list(getattr(item, "columns", []) or []) or None,
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.TabsItem):
        tabs = [
            ast.TabItem(
                label=tab.label,
                children=[_lower_page_item(child) for child in tab.children],
                visibility=getattr(tab, "visibility", None),
                visibility_rule=getattr(tab, "visibility_rule", None),
                show_when=getattr(tab, "show_when", None),
                line=tab.line,
                column=tab.column,
            )
            for tab in item.tabs
        ]
        lowered = ast.TabsItem(
            tabs=tabs,
            default=item.default,
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.ChatItem):
        composer_attach_upload = str(getattr(item, "composer_attach_upload", "") or "").strip()
        lowered = ast.ChatItem(
            children=[_lower_page_item(child) for child in item.children],
            style=getattr(item, "style", "bubbles"),
            show_avatars=bool(getattr(item, "show_avatars", False)),
            group_messages=bool(getattr(item, "group_messages", True)),
            actions=list(getattr(item, "actions", []) or []),
            streaming=bool(getattr(item, "streaming", False)),
            attachments=bool(getattr(item, "attachments", False)),
            composer_placeholder=getattr(item, "composer_placeholder", None),
            composer_send_style=str(getattr(item, "composer_send_style", "icon") or "icon"),
            composer_attach_upload=(composer_attach_upload or None),
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.ModalItem):
        lowered = ast.ModalItem(
            label=item.label,
            children=[_lower_page_item(child) for child in item.children],
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.DrawerItem):
        lowered = ast.DrawerItem(
            label=item.label,
            children=[_lower_page_item(child) for child in item.children],
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.LoadingItem):
        lowered = ast.LoadingItem(
            variant=getattr(item, "variant", "spinner"),
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.SnackbarItem):
        lowered = ast.SnackbarItem(
            message=getattr(item, "message", ""),
            duration=getattr(item, "duration", 3000),
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.IconItem):
        lowered = ast.IconItem(
            name=getattr(item, "name", ""),
            size=getattr(item, "size", "medium"),
            role=getattr(item, "role", "decorative"),
            label=getattr(item, "label", None),
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.LightboxItem):
        lowered = ast.LightboxItem(
            images=list(getattr(item, "images", []) or []),
            start_index=getattr(item, "start_index", 0),
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.NumberItem):
        entries = [ast.NumberEntry(kind=e.kind, value=e.value, record_name=e.record_name, label=e.label, line=e.line, column=e.column) for e in item.entries]
        lowered = ast.NumberItem(
            entries=entries,
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    if isinstance(item, ast.ViewItem):
        lowered = ast.ViewItem(
            record_name=item.record_name,
            visibility=getattr(item, "visibility", None),
            visibility_rule=getattr(item, "visibility_rule", None),
            show_when=getattr(item, "show_when", None),
            debug_only=getattr(item, "debug_only", None),
            line=item.line,
            column=item.column,
        )
        _copy_page_metadata(lowered, item)
        return lowered
    return item


def _lower_card_stat(stat: ast.CardStat | None) -> ast.CardStat | None:
    if stat is None:
        return None
    return ast.CardStat(value=_lower_expression(stat.value), label=stat.label, line=stat.line, column=stat.column)


def _lower_card_actions(actions: list[ast.CardAction] | None) -> list[ast.CardAction] | None:
    if actions is None:
        return None
    return [
        ast.CardAction(
            label=action.label,
            flow_name=action.flow_name,
            kind=action.kind,
            target=action.target,
            line=action.line,
            column=action.column,
        )
        for action in actions
    ]


def _copy_style_metadata(target, source) -> None:
    variant = getattr(source, "variant", None)
    if variant is not None:
        setattr(target, "variant", variant)
    style_hooks = getattr(source, "style_hooks", None)
    if style_hooks is not None:
        setattr(target, "style_hooks", dict(style_hooks))


def _copy_page_metadata(target, source) -> None:
    show_when = getattr(source, "show_when", None)
    if show_when is not None:
        setattr(target, "show_when", show_when)
    theme_overrides = getattr(source, "theme_overrides", None)
    if theme_overrides is not None:
        setattr(target, "theme_overrides", theme_overrides)


__all__ = ["_lower_page_item"]
