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
from namel3ss.ir.lowering.program_capabilities import require_program_capabilities
from namel3ss.ir.lowering.responsive import lower_responsive_definition
from namel3ss.ir.lowering.program_validation import (
    _ensure_unique_pages,
    _lower_active_page_rules,
    _normalize_capabilities,
    _normalize_pack_allowlist,
    _validate_chat_composers,
    _validate_page_style_hook_tokens,
    _validate_responsive_theme_scales,
    _validate_text_inputs,
    _validate_unique_upload_requests,
)
from namel3ss.ir.validation.ui_layout_validation import validate_ui_layout
from namel3ss.ir.validation.ui_rag_validation import validate_ui_rag
from namel3ss.ir.validation.ui_theme_validation import validate_ui_theme
from namel3ss.ir.model.agents import RunAgentsParallelStmt
from namel3ss.ir.model.program import Flow, Program
from namel3ss.ir.model.statements import ThemeChange, If, Repeat, RepeatWhile, ForEach, Match, MatchCase, TryCatch, ParallelBlock
from namel3ss.schema import records as schema
from namel3ss.theme import resolve_theme_definition, resolve_token_registry
from namel3ss.theme.ui_theme_tokens import UI_STYLE_THEME_DEFAULT, UI_STYLE_THEME_NAMES, compile_ui_theme
from namel3ss.ui.plugins import load_ui_plugin_registry
from namel3ss.ui.plugins.hooks import build_extension_hook_manager
from namel3ss.ui.settings import (
    UI_RUNTIME_THEME_VALUES,
    explicit_ui_theme_tokens,
    normalize_ui_settings,
    runtime_theme_setting_from_ui,
)
from namel3ss.validation import ValidationMode
from namel3ss.pipelines.registry import pipeline_contracts
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
    require_program_capabilities(
        capabilities,
        tool_map,
        job_irs,
        flow_irs,
        function_map,
        ai_map,
        agent_map,
    )
    responsive_layout = lower_responsive_definition(
        getattr(program, "responsive_definition", None),
        capabilities=capabilities,
    )
    theme_resolution = resolve_theme_definition(
        getattr(program, "theme_definition", None),
        capabilities=capabilities,
    )
    _validate_responsive_theme_scales(
        responsive_tokens=theme_resolution.responsive_tokens,
        responsive_layout=responsive_layout,
        line=getattr(getattr(theme_resolution, "definition", None), "line", None),
        column=getattr(getattr(theme_resolution, "definition", None), "column", None),
    )
    plugin_decls = tuple(getattr(program, "plugin_uses", []) or [])
    plugin_names = tuple(str(getattr(plugin, "name", "") or "") for plugin in plugin_decls)
    if plugin_names:
        missing_plugin_caps = [name for name in ("custom_ui", "sandbox") if name not in capabilities]
        if missing_plugin_caps:
            missing_text = ", ".join(missing_plugin_caps)
            example_caps = "\n  ".join(["custom_ui", "sandbox"])
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Missing capabilities: {missing_text}.",
                    why="UI plug-ins require explicit capability opt-in for custom UI rendering and sandbox isolation.",
                    fix="Add the missing capabilities to the capabilities block.",
                    example=f"capabilities:\n  {example_caps}",
                )
            )
    plugin_registry = load_ui_plugin_registry(
        plugin_names=plugin_names,
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
        allowed_capabilities=capabilities,
    )
    hook_manager = build_extension_hook_manager(
        plugin_registry=plugin_registry,
        capabilities=capabilities,
    )
    compile_hook_warnings = hook_manager.run_compile_hooks(program=program)
    pack_allowlist = _normalize_pack_allowlist(getattr(program, "pack_allowlist", None))
    pack_index = build_pack_index(getattr(program, "ui_packs", []))
    pattern_index = build_pattern_index(getattr(program, "ui_patterns", []), pack_index)
    page_names = {page.name for page in program.pages}
    pages = [
        _lower_page(
            page,
            record_map,
            flow_names,
            page_names,
            pack_index,
            pattern_index,
            plugin_registry,
            capabilities=capabilities,
        )
        for page in program.pages
    ]
    validate_ui_layout(pages, capabilities)
    validate_ui_theme(pages, capabilities)
    validate_ui_rag(pages, capabilities)
    ui_active_page_rules = _lower_active_page_rules(
        getattr(program, "ui_active_page_rules", None),
        page_names,
    )
    _ensure_unique_pages(pages)
    _validate_unique_upload_requests(pages)
    _validate_text_inputs(pages, flow_irs, flow_contracts)
    _validate_chat_composers(pages, flow_irs, flow_contracts)
    theme_runtime_supported = any(_flow_has_theme_change(flow) for flow in flow_irs)
    raw_ui_settings = getattr(program, "ui_settings", None)
    ui_settings = normalize_ui_settings(raw_ui_settings)
    if theme_resolution.ui_overrides:
        ui_settings = normalize_ui_settings({**ui_settings, **theme_resolution.ui_overrides})
    candidate_ui_theme = str(ui_settings.get("theme", program.app_theme))
    theme_setting = runtime_theme_setting_from_ui(raw_ui_settings, program.app_theme, normalized_theme=candidate_ui_theme)
    if theme_setting not in UI_RUNTIME_THEME_VALUES:
        theme_setting = program.app_theme
    visual_theme_name = candidate_ui_theme if candidate_ui_theme in UI_STYLE_THEME_NAMES else UI_STYLE_THEME_DEFAULT
    visual_theme = compile_ui_theme(visual_theme_name, explicit_ui_theme_tokens(raw_ui_settings))
    legacy_theme_tokens = {name: val for name, (val, _, _) in program.theme_tokens.items()}
    merged_theme_tokens = resolve_token_registry(theme_resolution, legacy_tokens=legacy_theme_tokens)
    _validate_page_style_hook_tokens(pages, merged_theme_tokens)
    lowered = Program(
        spec_version=str(program.spec_version),
        theme=theme_setting,
        theme_tokens=merged_theme_tokens,
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
        ui_plugins=plugin_registry.plugin_names,
        line=program.line,
        column=program.column,
    )
    setattr(lowered, "pack_allowlist", pack_allowlist)
    setattr(lowered, "ui_plugin_registry", plugin_registry)
    setattr(lowered, "extension_hook_manager", hook_manager)
    setattr(lowered, "extension_compile_warnings", compile_hook_warnings)
    setattr(lowered, "theme_definition", theme_resolution.definition)
    setattr(lowered, "resolved_theme", theme_resolution)
    setattr(lowered, "responsive_theme_tokens", theme_resolution.responsive_tokens)
    setattr(lowered, "responsive_layout", responsive_layout)
    setattr(lowered, "ui_visual_theme_name", visual_theme.theme_name)
    setattr(lowered, "ui_visual_theme_tokens", dict(visual_theme.tokens))
    setattr(lowered, "ui_visual_theme_css", visual_theme.css)
    setattr(lowered, "ui_visual_theme_css_hash", visual_theme.css_hash)
    setattr(lowered, "ui_visual_theme_font_url", visual_theme.font_url)
    return lowered
