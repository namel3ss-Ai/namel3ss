from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar.lowering.expressions import _lower_expression
from namel3ss.parser.sugar.lowering.statements import _lower_statements


def lower_program(program: ast.Program) -> ast.Program:
    return ast.Program(
        spec_version=program.spec_version,
        app_theme=program.app_theme,
        app_theme_line=program.app_theme_line,
        app_theme_column=program.app_theme_column,
        theme_tokens=program.theme_tokens,
        theme_preference=program.theme_preference,
        records=[_lower_record(record) for record in program.records],
        functions=[_lower_function(func) for func in getattr(program, "functions", [])],
        flows=[_lower_flow(flow) for flow in program.flows],
        pages=[_lower_page(page) for page in program.pages],
        ui_packs=[_lower_ui_pack(pack) for pack in getattr(program, "ui_packs", [])],
        ais=list(program.ais),
        tools=list(program.tools),
        agents=list(program.agents),
        uses=list(program.uses),
        capsule=program.capsule,
        identity=_lower_identity(program.identity) if program.identity else None,
        line=program.line,
        column=program.column,
    )


def _lower_flow(flow: ast.Flow) -> ast.Flow:
    return ast.Flow(
        name=flow.name,
        body=_lower_statements(flow.body),
        requires=_lower_expression(flow.requires) if flow.requires else None,
        audited=flow.audited,
        line=flow.line,
        column=flow.column,
    )


def _lower_function(func: ast.FunctionDecl) -> ast.FunctionDecl:
    return ast.FunctionDecl(
        name=func.name,
        signature=func.signature,
        body=_lower_statements(func.body),
        line=func.line,
        column=func.column,
    )


def _lower_page(page: ast.PageDecl) -> ast.PageDecl:
    return ast.PageDecl(
        name=page.name,
        items=[_lower_page_item(item) for item in page.items],
        requires=_lower_expression(page.requires) if page.requires else None,
        line=page.line,
        column=page.column,
    )


def _lower_ui_pack(pack: ast.UIPackDecl) -> ast.UIPackDecl:
    fragments = [
        ast.UIPackFragment(
            name=fragment.name,
            items=[_lower_page_item(item) for item in fragment.items],
            line=fragment.line,
            column=fragment.column,
        )
        for fragment in pack.fragments
    ]
    return ast.UIPackDecl(
        name=pack.name,
        version=pack.version,
        fragments=fragments,
        line=pack.line,
        column=pack.column,
    )


def _lower_page_item(item: ast.PageItem) -> ast.PageItem:
    if isinstance(item, ast.CardItem):
        children = [_lower_page_item(child) for child in item.children]
        stat = _lower_card_stat(item.stat)
        actions = _lower_card_actions(item.actions)
        return ast.CardItem(
            label=item.label,
            children=children,
            stat=stat,
            actions=actions,
            line=item.line,
            column=item.column,
        )
    if isinstance(item, ast.CardGroupItem):
        children = [_lower_page_item(child) for child in item.children]
        return ast.CardGroupItem(children=children, line=item.line, column=item.column)
    if isinstance(item, ast.RowItem):
        children = [_lower_page_item(child) for child in item.children]
        return ast.RowItem(children=children, line=item.line, column=item.column)
    if isinstance(item, ast.ColumnItem):
        children = [_lower_page_item(child) for child in item.children]
        return ast.ColumnItem(children=children, line=item.line, column=item.column)
    if isinstance(item, ast.SectionItem):
        children = [_lower_page_item(child) for child in item.children]
        return ast.SectionItem(label=item.label, children=children, line=item.line, column=item.column)
    if isinstance(item, ast.TabsItem):
        tabs = [
            ast.TabItem(label=tab.label, children=[_lower_page_item(child) for child in tab.children], line=tab.line, column=tab.column)
            for tab in item.tabs
        ]
        return ast.TabsItem(tabs=tabs, default=item.default, line=item.line, column=item.column)
    if isinstance(item, ast.ChatItem):
        return ast.ChatItem(children=[_lower_page_item(child) for child in item.children], line=item.line, column=item.column)
    if isinstance(item, ast.ModalItem):
        return ast.ModalItem(label=item.label, children=[_lower_page_item(child) for child in item.children], line=item.line, column=item.column)
    if isinstance(item, ast.DrawerItem):
        return ast.DrawerItem(label=item.label, children=[_lower_page_item(child) for child in item.children], line=item.line, column=item.column)
    return item


def _lower_card_stat(stat: ast.CardStat | None) -> ast.CardStat | None:
    if stat is None:
        return None
    return ast.CardStat(
        value=_lower_expression(stat.value),
        label=stat.label,
        line=stat.line,
        column=stat.column,
    )


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


def _lower_record(record: ast.RecordDecl) -> ast.RecordDecl:
    return ast.RecordDecl(
        name=record.name,
        fields=[_lower_field(field) for field in record.fields],
        tenant_key=_lower_expression(record.tenant_key) if record.tenant_key else None,
        ttl_hours=_lower_expression(record.ttl_hours) if record.ttl_hours else None,
        line=record.line,
        column=record.column,
    )


def _lower_identity(identity: ast.IdentityDecl) -> ast.IdentityDecl:
    return ast.IdentityDecl(
        name=identity.name,
        fields=[_lower_field(field) for field in identity.fields],
        trust_levels=identity.trust_levels,
        line=identity.line,
        column=identity.column,
    )


def _lower_field(field: ast.FieldDecl) -> ast.FieldDecl:
    return ast.FieldDecl(
        name=field.name,
        type_name=field.type_name,
        constraint=_lower_constraint(field.constraint),
        type_was_alias=field.type_was_alias,
        raw_type_name=field.raw_type_name,
        type_line=field.type_line,
        type_column=field.type_column,
        line=field.line,
        column=field.column,
    )


def _lower_constraint(constraint: ast.FieldConstraint | None) -> ast.FieldConstraint | None:
    if constraint is None:
        return None
    return ast.FieldConstraint(
        kind=constraint.kind,
        expression=_lower_expression(constraint.expression) if constraint.expression else None,
        expression_high=_lower_expression(constraint.expression_high) if constraint.expression_high else None,
        pattern=constraint.pattern,
        line=constraint.line,
        column=constraint.column,
    )
