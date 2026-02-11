from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar.lowering.expressions import _lower_expression
from namel3ss.parser.sugar.lowering.flow_steps import _lower_flow_steps
from namel3ss.parser.sugar.lowering.statements import _lower_statements
from namel3ss.parser.sugar.lowering.ai_flows import ai_flow_to_flow, lower_ai_flow
from namel3ss.parser.sugar.lowering.crud import expand_crud_routes
from namel3ss.parser.sugar.lowering.program_page_items import _lower_page_item


def lower_program(program: ast.Program) -> ast.Program:
    lowered_ai_flows = [lower_ai_flow(flow) for flow in getattr(program, "ai_flows", []) or []]
    lowered_prompts = [_lower_prompt(prompt) for prompt in getattr(program, "prompts", []) or []]
    lowered_crud = [_lower_crud(crud) for crud in getattr(program, "crud", []) or []]
    expanded_routes = list(getattr(program, "routes", []) or [])
    expanded_routes.extend(expand_crud_routes(lowered_crud))
    expanded_flows = [_lower_flow(flow) for flow in program.flows]
    expanded_flows.extend(ai_flow_to_flow(flow) for flow in lowered_ai_flows)
    lowered = ast.Program(
        spec_version=program.spec_version,
        app_theme=program.app_theme,
        app_theme_line=program.app_theme_line,
        app_theme_column=program.app_theme_column,
        theme_tokens=program.theme_tokens,
        theme_preference=program.theme_preference,
        ui_settings=program.ui_settings,
        ui_line=getattr(program, "ui_line", None),
        ui_column=getattr(program, "ui_column", None),
        ui_active_page_rules=_lower_active_page_rules(program.ui_active_page_rules)
        if program.ui_active_page_rules
        else None,
        capabilities=list(getattr(program, "capabilities", []) or []),
        records=[_lower_record(record) for record in program.records],
        functions=[_lower_function(func) for func in getattr(program, "functions", [])],
        contracts=[_lower_contract(contract) for contract in getattr(program, "contracts", [])],
        flows=expanded_flows,
        routes=expanded_routes,
        crud=lowered_crud,
        prompts=lowered_prompts,
        ai_flows=lowered_ai_flows,
        jobs=[_lower_job(job) for job in getattr(program, "jobs", [])],
        pages=[_lower_page(page) for page in program.pages],
        ui_packs=[_lower_ui_pack(pack) for pack in getattr(program, "ui_packs", [])],
        ui_patterns=[_lower_ui_pattern(pattern) for pattern in getattr(program, "ui_patterns", [])],
        ais=list(program.ais),
        tools=list(program.tools),
        agents=list(program.agents),
        agent_team=getattr(program, "agent_team", None),
        uses=list(program.uses),
        includes=list(getattr(program, "includes", []) or []),
        plugin_uses=list(getattr(program, "plugin_uses", []) or []),
        capsule=program.capsule,
        identity=_lower_identity(program.identity) if program.identity else None,
        policy=_lower_policy(program.policy) if program.policy else None,
        line=program.line,
        column=program.column,
    )
    lowered_navigation = getattr(program, "ui_navigation", None)
    if lowered_navigation is not None:
        setattr(lowered, "ui_navigation", lowered_navigation)
    lowered_ui_state = getattr(program, "ui_state", None)
    if lowered_ui_state is not None:
        setattr(lowered, "ui_state", lowered_ui_state)
    lowered_app_permissions = getattr(program, "app_permissions", None)
    if lowered_app_permissions is not None:
        setattr(lowered, "app_permissions", lowered_app_permissions)
    raw_allowlist = getattr(program, "pack_allowlist", None)
    setattr(lowered, "pack_allowlist", list(raw_allowlist) if raw_allowlist is not None else None)
    setattr(lowered, "theme_definition", getattr(program, "theme_definition", None))
    setattr(lowered, "theme_line", getattr(program, "theme_line", None))
    setattr(lowered, "theme_column", getattr(program, "theme_column", None))
    setattr(lowered, "responsive_definition", getattr(program, "responsive_definition", None))
    setattr(lowered, "responsive_line", getattr(program, "responsive_line", None))
    setattr(lowered, "responsive_column", getattr(program, "responsive_column", None))
    return lowered


def _lower_active_page_rules(rules: list[ast.ActivePageRule]) -> list[ast.ActivePageRule]:
    lowered: list[ast.ActivePageRule] = []
    for rule in rules:
        lowered.append(
            ast.ActivePageRule(
                page_name=rule.page_name,
                path=_lower_expression(rule.path),
                value=_lower_expression(rule.value),
                line=rule.line,
                column=rule.column,
            )
        )
    return lowered


def _lower_flow(flow: ast.Flow) -> ast.Flow:
    return ast.Flow(
        name=flow.name,
        body=_lower_statements(flow.body),
        requires=_lower_expression(flow.requires) if flow.requires else None,
        audited=flow.audited,
        purity=getattr(flow, "purity", "effectful"),
        steps=_lower_flow_steps(getattr(flow, "steps", None)),
        declarative=bool(getattr(flow, "declarative", False)),
        ai_metadata=_lower_ai_metadata(getattr(flow, "ai_metadata", None)),
        line=flow.line,
        column=flow.column,
    )


def _lower_ai_metadata(metadata: ast.AIFlowMetadata | None) -> ast.AIFlowMetadata | None:
    if metadata is None:
        return None
    output_fields = None
    if metadata.output_fields:
        output_fields = [
            ast.AIOutputField(
                name=field.name,
                type_name=field.type_name,
                line=field.line,
                column=field.column,
            )
            for field in metadata.output_fields
        ]
    chain_steps = None
    if metadata.chain_steps:
        chain_steps = [
            ast.ChainStep(
                flow_kind=step.flow_kind,
                flow_name=step.flow_name,
                input_expr=_lower_expression(step.input_expr),
                line=step.line,
                column=step.column,
            )
            for step in metadata.chain_steps
        ]
    tests = None
    if metadata.tests:
        tests = ast.AIFlowTestConfig(
            dataset=metadata.tests.dataset,
            metrics=list(metadata.tests.metrics),
            line=metadata.tests.line,
            column=metadata.tests.column,
        )
    return ast.AIFlowMetadata(
        model=metadata.model,
        prompt=metadata.prompt,
        prompt_expr=_lower_expression(metadata.prompt_expr) if metadata.prompt_expr else None,
        dataset=metadata.dataset,
        kind=getattr(metadata, "kind", None),
        output_type=getattr(metadata, "output_type", None),
        source_language=getattr(metadata, "source_language", None),
        target_language=getattr(metadata, "target_language", None),
        output_fields=output_fields,
        labels=list(getattr(metadata, "labels", []) or []) or None,
        sources=list(getattr(metadata, "sources", []) or []) or None,
        chain_steps=chain_steps,
        tests=tests,
        line=metadata.line,
        column=metadata.column,
    )


def _lower_job(job: ast.JobDecl) -> ast.JobDecl:
    return ast.JobDecl(
        name=job.name,
        body=_lower_statements(job.body),
        when=_lower_expression(job.when) if job.when else None,
        line=job.line,
        column=job.column,
    )


def _lower_prompt(prompt: ast.PromptDefinition) -> ast.PromptDefinition:
    return ast.PromptDefinition(
        name=prompt.name,
        version=prompt.version,
        text=prompt.text,
        description=prompt.description,
        line=prompt.line,
        column=prompt.column,
    )


def _lower_crud(crud: ast.CrudDefinition) -> ast.CrudDefinition:
    return ast.CrudDefinition(
        record_name=crud.record_name,
        line=crud.line,
        column=crud.column,
    )


def _lower_function(func: ast.FunctionDecl) -> ast.FunctionDecl:
    return ast.FunctionDecl(
        name=func.name,
        signature=func.signature,
        body=_lower_statements(func.body),
        line=func.line,
        column=func.column,
    )


def _lower_contract(contract: ast.ContractDecl) -> ast.ContractDecl:
    return ast.ContractDecl(
        kind=contract.kind,
        name=contract.name,
        signature=contract.signature,
        line=contract.line,
        column=contract.column,
    )


def _lower_page(page: ast.PageDecl) -> ast.PageDecl:
    lowered_page = ast.PageDecl(
        name=page.name,
        items=[_lower_page_item(item) for item in page.items],
        layout=_lower_page_layout(getattr(page, "layout", None)),
        requires=_lower_expression(page.requires) if page.requires else None,
        visibility=_lower_expression(page.visibility) if getattr(page, "visibility", None) else None,
        visibility_rule=getattr(page, "visibility_rule", None),
        purpose=getattr(page, "purpose", None),
        state_defaults=getattr(page, "state_defaults", None),
        status=_lower_status_block(getattr(page, "status", None)),
        debug_only=getattr(page, "debug_only", None),
        diagnostics=getattr(page, "diagnostics", None),
        theme_tokens=getattr(page, "theme_tokens", None),
        line=page.line,
        column=page.column,
    )
    lowered_navigation = getattr(page, "ui_navigation", None)
    if lowered_navigation is not None:
        setattr(lowered_page, "ui_navigation", lowered_navigation)
    return lowered_page


def _lower_page_layout(layout: ast.PageLayout | None) -> ast.PageLayout | None:
    if layout is None:
        return None
    return ast.PageLayout(
        header=[_lower_page_item(item) for item in layout.header],
        sidebar_left=[_lower_page_item(item) for item in layout.sidebar_left],
        main=[_lower_page_item(item) for item in layout.main],
        drawer_right=[_lower_page_item(item) for item in layout.drawer_right],
        footer=[_lower_page_item(item) for item in layout.footer],
        diagnostics=[_lower_page_item(item) for item in layout.diagnostics],
        line=layout.line,
        column=layout.column,
    )


def _lower_status_block(status: ast.StatusBlock | None) -> ast.StatusBlock | None:
    if status is None:
        return None
    cases: list[ast.StatusCase] = []
    for case in status.cases:
        condition = case.condition
        lowered_condition = ast.StatusCondition(
            path=_lower_expression(condition.path),
            kind=condition.kind,
            value=_lower_expression(condition.value) if condition.value is not None else None,
            line=condition.line,
            column=condition.column,
        )
        cases.append(
            ast.StatusCase(
                name=case.name,
                condition=lowered_condition,
                items=[_lower_page_item(item) for item in case.items],
                line=case.line,
                column=case.column,
            )
        )
    return ast.StatusBlock(cases=cases, line=status.line, column=status.column)


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


def _lower_ui_pattern(pattern: ast.UIPatternDecl) -> ast.UIPatternDecl:
    params = [
        ast.PatternParam(
            name=param.name,
            kind=param.kind,
            optional=bool(getattr(param, "optional", False)),
            default=getattr(param, "default", None),
            line=param.line,
            column=param.column,
        )
        for param in getattr(pattern, "parameters", [])
    ]
    return ast.UIPatternDecl(
        name=pattern.name,
        parameters=params,
        items=[_lower_page_item(item) for item in pattern.items],
        line=pattern.line,
        column=pattern.column,
    )


def _lower_record(record: ast.RecordDecl) -> ast.RecordDecl:
    lowered = ast.RecordDecl(
        name=record.name,
        fields=[_lower_field(field) for field in record.fields],
        tenant_key=_lower_expression(record.tenant_key) if record.tenant_key else None,
        ttl_hours=_lower_expression(record.ttl_hours) if record.ttl_hours else None,
        line=record.line,
        column=record.column,
    )
    setattr(lowered, "version", getattr(record, "version", None))
    return lowered


def _lower_identity(identity: ast.IdentityDecl) -> ast.IdentityDecl:
    return ast.IdentityDecl(
        name=identity.name,
        fields=[_lower_field(field) for field in identity.fields],
        trust_levels=identity.trust_levels,
        line=identity.line,
        column=identity.column,
    )


def _lower_policy(policy: ast.PolicyDecl) -> ast.PolicyDecl:
    return ast.PolicyDecl(
        rules=[_lower_policy_rule(rule) for rule in policy.rules],
        line=policy.line,
        column=policy.column,
    )


def _lower_policy_rule(rule: ast.PolicyRuleDecl) -> ast.PolicyRuleDecl:
    return ast.PolicyRuleDecl(action=rule.action, mode=rule.mode, permissions=list(rule.permissions), line=rule.line, column=rule.column)


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
