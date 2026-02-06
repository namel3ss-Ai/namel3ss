from __future__ import annotations
from typing import Dict, List
from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir.lowering.agents import _lower_agent_team, _lower_agents
from namel3ss.ir.lowering.ai import _lower_ai_decls
from namel3ss.ir.lowering.flow import lower_flow
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.lowering.contracts import lower_flow_contracts
from namel3ss.ir.lowering.jobs import lower_jobs
from namel3ss.ir.lowering.routes import lower_routes
from namel3ss.ir.lowering.prompts import lower_prompts
from namel3ss.ir.lowering.ai_flows import lower_ai_flows
from namel3ss.ir.lowering.crud import lower_crud
from namel3ss.compiler.routes import validate_routes
from namel3ss.compiler.prompts import validate_prompts, validate_prompt_references
from namel3ss.compiler.ai_flows import validate_ai_flows
from namel3ss.compiler.crud import validate_crud
from namel3ss.ir.lowering.policy import lower_policy
from namel3ss.flow_contract import (
    validate_declarative_flows,
    validate_flow_names,
    validate_flow_contracts,
    validate_flow_composition,
    validate_flow_purity,
)
from namel3ss.ir.functions.lowering import lower_functions
from namel3ss.ir.lowering.identity import _lower_identity
from namel3ss.ir.lowering.pages import _lower_page
from namel3ss.ir.lowering.records import _lower_record
from namel3ss.ir.lowering.tools import _lower_tools
from namel3ss.ir.lowering.ui_packs import build_pack_index
from namel3ss.ir.lowering.ui_patterns import build_pattern_index
from namel3ss.ir.model.agents import RunAgentsParallelStmt
from namel3ss.ir.model.flow_steps import FlowInput
from namel3ss.ir.model.contracts import ContractDecl
from namel3ss.ir.model.program import Flow, Program
from namel3ss.ir.model.pages import (
    ActivePageRule,
    CardGroupItem,
    CardItem,
    ChatItem,
    ChatComposerItem,
    ColumnItem,
    ComposeItem,
    DrawerItem,
    ModalItem,
    Page,
    RowItem,
    SectionItem,
    TabsItem,
    TextInputItem,
)
from namel3ss.ir.model.expressions import Literal as IRLiteral
from namel3ss.ir.model.expressions import StatePath as IRStatePath
from namel3ss.ir.model.statements import ThemeChange, If, Repeat, RepeatWhile, ForEach, Match, MatchCase, TryCatch, ParallelBlock
from namel3ss.schema import records as schema
from namel3ss.ui.settings import normalize_ui_settings
from namel3ss.validation import ValidationMode
from namel3ss.lang.capabilities import normalize_builtin_capability
from namel3ss.pipelines.registry import pipeline_contracts
from namel3ss.utils.numbers import is_number, to_decimal
def _statement_has_theme_change(stmt) -> bool:
    if isinstance(stmt, ThemeChange):
        return True
    if isinstance(stmt, If):
        return any(_statement_has_theme_change(s) for s in stmt.then_body) or any(_statement_has_theme_change(s) for s in stmt.else_body)
    if isinstance(stmt, Repeat):
        return any(_statement_has_theme_change(s) for s in stmt.body)
    if isinstance(stmt, RepeatWhile):
        return any(_statement_has_theme_change(s) for s in stmt.body)
    if isinstance(stmt, ForEach):
        return any(_statement_has_theme_change(s) for s in stmt.body)
    if isinstance(stmt, Match):
        return any(_statement_has_theme_change(c) for c in stmt.cases) or (any(_statement_has_theme_change(s) for s in stmt.otherwise) if stmt.otherwise else False)
    if isinstance(stmt, MatchCase):
        return any(_statement_has_theme_change(s) for s in stmt.body)
    if isinstance(stmt, TryCatch):
        return any(_statement_has_theme_change(s) for s in stmt.try_body) or any(_statement_has_theme_change(s) for s in stmt.catch_body)
    if isinstance(stmt, ParallelBlock):
        return any(_statement_has_theme_change(s) for task in stmt.tasks for s in task.body)
    if isinstance(stmt, RunAgentsParallelStmt):
        return any(_statement_has_theme_change(e) for e in stmt.entries)
    return False
def _flow_has_theme_change(flow: Flow) -> bool:
    return any(_statement_has_theme_change(stmt) for stmt in flow.body)
def lower_program(program: ast.Program) -> Program:
    if not getattr(program, "spec_version", None):
        raise Namel3ssError(
            build_guidance_message(
                what="Spec declaration is missing.",
                why="Programs must declare a spec version before lowering.",
                fix='Add a spec declaration at the top of the file.',
                example='spec is \"1.0\"',
            )
        )
    record_schemas = [_lower_record(record) for record in program.records]
    identity_schema = _lower_identity(program.identity) if program.identity else None
    tool_map = _lower_tools(program.tools)
    ai_map = _lower_ai_decls(program.ais, tool_map)
    agent_team = _lower_agent_team(getattr(program, "agent_team", None), program.agents)
    agent_map = _lower_agents(program.agents, ai_map, agent_team)
    function_map = lower_functions(program.functions, agent_map)
    flow_contracts = lower_flow_contracts(getattr(program, "contracts", []) or [])
    flow_irs: List[Flow] = [lower_flow(flow, agent_map) for flow in program.flows]
    job_irs = lower_jobs(getattr(program, "jobs", []), agent_map)
    record_map: Dict[str, schema.RecordSchema] = {rec.name: rec for rec in record_schemas}
    flow_names = validate_flow_names(flow_irs)
    prompt_names = validate_prompts(getattr(program, "prompts", []) or [])
    validate_prompt_references(
        getattr(program, "flows", []) or [],
        getattr(program, "ai_flows", []) or [],
        prompt_names=prompt_names,
    )
    ai_decls = list(getattr(program, "ai_flows", []) or [])
    known_flow_names = {flow.name for flow in getattr(program, "flows", []) or []}
    known_flow_names.update(flow.name for flow in ai_decls)
    validate_ai_flows(
        ai_decls,
        record_names=set(record_map.keys()),
        known_flow_names=known_flow_names,
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
    )
    validate_crud(getattr(program, "crud", []) or [], record_names=set(record_map.keys()))
    validate_routes(getattr(program, "routes", []) or [], record_names=set(record_map.keys()), flow_names=set(flow_names))
    validate_flow_contracts(flow_irs, flow_contracts)
    validate_flow_composition(flow_irs, flow_contracts, pipeline_contracts())
    validate_flow_purity(flow_irs, flow_contracts)
    validate_declarative_flows(flow_irs, record_map, tool_map, mode=ValidationMode.RUNTIME, warnings=None)
    capabilities = _normalize_capabilities(getattr(program, "capabilities", []) or [])
    _require_capabilities(capabilities, tool_map, job_irs)
    pack_allowlist = _normalize_pack_allowlist(getattr(program, "pack_allowlist", None))
    pack_index = build_pack_index(getattr(program, "ui_packs", []))
    pattern_index = build_pattern_index(getattr(program, "ui_patterns", []), pack_index)
    page_names = {page.name for page in program.pages}
    pages = [
        _lower_page(page, record_map, flow_names, page_names, pack_index, pattern_index)
        for page in program.pages
    ]
    ui_active_page_rules = _lower_active_page_rules(
        getattr(program, "ui_active_page_rules", None),
        page_names,
    )
    _ensure_unique_pages(pages)
    _validate_text_inputs(pages, flow_irs, flow_contracts)
    _validate_chat_composers(pages, flow_irs, flow_contracts)
    theme_runtime_supported = any(_flow_has_theme_change(flow) for flow in flow_irs)
    ui_settings = normalize_ui_settings(getattr(program, "ui_settings", None))
    theme_setting = ui_settings.get("theme", program.app_theme)
    lowered = Program(
        spec_version=str(program.spec_version),
        theme=theme_setting,
        theme_tokens={name: val for name, (val, _, _) in program.theme_tokens.items()},
        theme_runtime_supported=theme_runtime_supported,
        theme_preference={
            "allow_override": program.theme_preference.get("allow_override", (False, None, None))[0],
            "persist": program.theme_preference.get("persist", ("none", None, None))[0],
        },
        ui_settings=ui_settings,
        capabilities=capabilities,
        records=record_schemas,
        functions=function_map,
        flow_contracts=flow_contracts,
        flows=flow_irs,
        routes=lower_routes(getattr(program, "routes", []) or []),
        crud=lower_crud(getattr(program, "crud", []) or []),
        prompts=lower_prompts(getattr(program, "prompts", []) or []),
        ai_flows=lower_ai_flows(getattr(program, "ai_flows", []) or []),
        jobs=job_irs,
        pages=pages,
        ais=ai_map,
        tools=tool_map,
        agents=agent_map,
        policy=lower_policy(getattr(program, "policy", None)),
        agent_team=agent_team,
        identity=identity_schema,
        state_defaults=getattr(program, "state_defaults", None),
        ui_active_page_rules=ui_active_page_rules,
        line=program.line,
        column=program.column,
    )
    setattr(lowered, "pack_allowlist", pack_allowlist)
    return lowered
def _ensure_unique_pages(pages: list[Page]) -> None:
    seen: dict[str, object] = {}
    for page in pages:
        if page.name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Page '{page.name}' is declared more than once.",
                    why="Pages must have unique names.",
                    fix="Rename the duplicate page or merge its contents.",
                    example='page "home":',
                ),
                line=getattr(page, "line", None),
                column=getattr(page, "column", None),
            )
        seen[page.name] = True
def _lower_active_page_rules(
    rules: list[ast.ActivePageRule] | None,
    page_names: set[str],
) -> list[ActivePageRule] | None:
    if not rules:
        return None
    lowered: list[ActivePageRule] = []
    seen: dict[tuple[tuple[str, ...], object], str] = {}
    for rule in rules:
        if not isinstance(rule, ast.ActivePageRule):
            raise Namel3ssError(
                "Active page rules require: is \"<page>\" only when state.<path> is <value>.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        if rule.page_name not in page_names:
            raise Namel3ssError(
                f"Active page rule references unknown page '{rule.page_name}'.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        lowered_path = _lower_expression(rule.path)
        if not isinstance(lowered_path, IRStatePath):
            raise Namel3ssError(
                "Active page rules require state.<path>.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        lowered_value = _lower_expression(rule.value)
        if not isinstance(lowered_value, IRLiteral):
            raise Namel3ssError(
                "Active page rules require a text, number, or boolean literal.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        key = _active_page_rule_key(lowered_path.path, lowered_value.value)
        if key in seen:
            raise Namel3ssError(
                "Active page rules must be unique for each state value.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        seen[key] = rule.page_name
        lowered.append(
            ActivePageRule(
                page_name=rule.page_name,
                path=lowered_path,
                value=lowered_value,
                line=rule.line,
                column=rule.column,
            )
        )
    return lowered
def _active_page_rule_key(path: list[str], value: object) -> tuple[tuple[str, ...], object]:
    if is_number(value):
        return (tuple(path), to_decimal(value))
    return (tuple(path), value)
def _validate_text_inputs(
    pages: list[Page],
    flows: list[Flow],
    flow_contracts: dict[str, ContractDecl],
) -> None:
    flow_inputs: dict[str, dict[str, str]] = {flow.name: _flow_input_signature(flow, flow_contracts) for flow in flows}
    for page in pages:
        for item in _walk_page_items(page.items):
            if not isinstance(item, TextInputItem):
                continue
            inputs = flow_inputs.get(item.flow_name) or {}
            if not inputs:
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Text input "{item.name}" targets flow "{item.flow_name}" without input fields.',
                        why="Text inputs require a flow input field with a text type.",
                        fix=f'Add an input block with `{item.name} is text` to the flow.',
                        example=f'flow "{item.flow_name}"\\n  input\\n    {item.name} is text',
                    ),
                    line=item.line,
                    column=item.column,
                )
            field_type = inputs.get(item.name)
            if field_type is None:
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Text input "{item.name}" is not declared on flow "{item.flow_name}".',
                        why="The input name must match a flow input field.",
                        fix=f'Add `{item.name} is text` to the flow input block.',
                        example=f'flow "{item.flow_name}"\\n  input\\n    {item.name} is text',
                    ),
                    line=item.line,
                    column=item.column,
                )
            if field_type != "text":
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Text input "{item.name}" must bind to a text field.',
                        why=f'Flow "{item.flow_name}" declares "{item.name}" as {field_type}.',
                        fix=f'Change the flow input type to text for "{item.name}".',
                        example=f'flow "{item.flow_name}"\\n  input\\n    {item.name} is text',
                    ),
                    line=item.line,
                    column=item.column,
                )
def _validate_chat_composers(
    pages: list[Page],
    flows: list[Flow],
    flow_contracts: dict[str, ContractDecl],
) -> None:
    flow_inputs: dict[str, dict[str, str]] = {flow.name: _flow_input_signature(flow, flow_contracts) for flow in flows}
    for page in pages:
        for item in _walk_page_items(page.items):
            if not isinstance(item, ChatComposerItem):
                continue
            inputs = flow_inputs.get(item.flow_name) or {}
            extra_fields = list(getattr(item, "fields", []) or [])
            if not extra_fields:
                if not inputs:
                    continue
                message_type = inputs.get("message")
                if message_type is None:
                    raise Namel3ssError(
                        build_guidance_message(
                            what=f'Chat composer for flow "{item.flow_name}" is missing "message" in inputs.',
                            why="Composer submissions always include message.",
                            fix='Add `message is text` to the flow input block.',
                            example=_composer_input_example(item.flow_name, ["message"]),
                        ),
                        line=item.line,
                        column=item.column,
                    )
                if message_type != "text":
                    raise Namel3ssError(
                        build_guidance_message(
                            what='Chat composer field "message" must be text.',
                            why=f'Flow "{item.flow_name}" declares "message" as {message_type}.',
                            fix='Change the flow input type to text for "message".',
                            example=f'flow "{item.flow_name}"\\n  input\\n    message is text',
                        ),
                        line=item.line,
                        column=item.column,
                    )
                continue
            expected_fields = _composer_expected_fields(extra_fields)
            if not inputs:
                example = _composer_input_example(item.flow_name, expected_fields)
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Chat composer for flow "{item.flow_name}" declares extra fields without flow inputs.',
                        why="Structured composers require explicit input fields for validation.",
                        fix="Add an input block that lists message and the extra fields.",
                        example=example,
                    ),
                    line=item.line,
                    column=item.column,
                )
            missing = [name for name in expected_fields if name not in inputs]
            extra = [name for name in inputs.keys() if name not in expected_fields]
            if missing or extra:
                why_parts: list[str] = []
                if missing:
                    why_parts.append(f"Missing: {', '.join(missing)}.")
                if extra:
                    why_parts.append(f"Extra: {', '.join(extra)}.")
                example = _composer_input_example(item.flow_name, expected_fields)
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Chat composer fields do not match flow "{item.flow_name}" inputs.',
                        why=" ".join(why_parts) if why_parts else "Flow inputs must match composer fields.",
                        fix="Update the flow input block to match the composer payload.",
                        example=example,
                    ),
                    line=item.line,
                    column=item.column,
                )
            type_map = {"message": "text"}
            for field in extra_fields:
                type_map[field.name] = field.type_name
            for name in expected_fields:
                expected_type = type_map.get(name)
                actual_type = inputs.get(name)
                if expected_type and actual_type and actual_type != expected_type:
                    field = next((entry for entry in extra_fields if entry.name == name), None)
                    raise Namel3ssError(
                        build_guidance_message(
                            what=f'Chat composer field "{name}" must be {expected_type}.',
                            why=f'Flow "{item.flow_name}" declares "{name}" as {actual_type}.',
                            fix=f'Change the flow input type to {expected_type} for "{name}".',
                            example=f'flow "{item.flow_name}"\\n  input\\n    {name} is {expected_type}',
                        ),
                        line=field.line if field else item.line,
                        column=field.column if field else item.column,
                    )
def _flow_input_signature(flow: Flow, flow_contracts: dict[str, ContractDecl]) -> dict[str, str]:
    if flow.steps:
        for step in flow.steps:
            if isinstance(step, FlowInput):
                return {field.name: field.type_name for field in step.fields}
    contract = flow_contracts.get(flow.name)
    if contract is None:
        return {}
    return {field.name: field.type_name for field in contract.signature.inputs}
def _composer_expected_fields(extra_fields: list[object]) -> list[str]:
    names = ["message"]
    for field in extra_fields:
        name = getattr(field, "name", None)
        if isinstance(name, str):
            names.append(name)
    return names
def _composer_input_example(flow_name: str, field_names: list[str]) -> str:
    lines = [f'flow "{flow_name}"', "  input"]
    for name in field_names:
        lines.append(f"    {name} is text")
    return "\\n".join(lines)
def _walk_page_items(items: list[object]) -> list[object]:
    collected: list[object] = []
    for item in items:
        collected.append(item)
        if isinstance(
            item,
            (
                SectionItem,
                CardGroupItem,
                CardItem,
                RowItem,
                ColumnItem,
                ComposeItem,
                DrawerItem,
                ModalItem,
                ChatItem,
            ),
        ):
            collected.extend(_walk_page_items(getattr(item, "children", [])))
            continue
        if isinstance(item, TabsItem):
            for tab in item.tabs:
                collected.extend(_walk_page_items(tab.children))
            continue
    return collected
def _normalize_capabilities(items: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for item in items:
        value = normalize_builtin_capability(item)
        if value:
            normalized.append(value)
    return tuple(sorted(set(normalized)))
def _normalize_pack_allowlist(items: list[str] | None) -> tuple[str, ...] | None:
    if items is None:
        return None
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    if not normalized:
        return None
    return tuple(normalized)
def _require_capabilities(
    allowed: tuple[str, ...],
    tools: Dict[str, object],
    jobs: list,
) -> None:
    required: set[str] = set()
    for tool in tools.values():
        kind = getattr(tool, "kind", None)
        if kind == "http":
            required.add("http")
        elif kind == "file":
            required.add("files")
    if jobs:
        required.add("jobs")
    missing = sorted(required - set(allowed))
    if not missing:
        return
    missing_text = ", ".join(missing)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Missing capabilities: {missing_text}.",
            why="Apps must explicitly enable built-in backend capabilities.",
            fix="Add a capabilities block that lists the missing entries.",
            example="capabilities:\n  http\n  jobs\n  files",
        )
    )
