from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.ir.nodes import lower_program
from namel3ss.lexer.tokens import KEYWORDS
from namel3ss.lint.semantic import lint_semantic
from namel3ss.lint.text_scan import scan_text
from namel3ss.lint.types import Finding
from namel3ss.lint.functions import lint_functions
from namel3ss.runtime.tools.bindings import bindings_path
from namel3ss.tools.health.analyze import analyze_tool_health
from namel3ss.types import normalize_type_name
from namel3ss.parser.core import parse
from namel3ss.ast import nodes as ast
from namel3ss.module_loader.types import ProjectLoadResult


def lint_source(source: str, strict: bool = True, allow_legacy_type_aliases: bool = True) -> list[Finding]:
    lines = source.splitlines()
    findings = scan_text(lines)

    ast_program = None
    try:
        ast_program = parse(source, allow_legacy_type_aliases=allow_legacy_type_aliases)
    except Namel3ssError as err:
        findings.append(
            Finding(
                code="lint.parse_failed",
                message="Parse failed; showing best-effort lint results.",
                line=err.line,
                column=err.column,
                severity="warning",
            )
        )
        return findings

    findings.extend(_lint_reserved_identifiers(ast_program))
    findings.extend(_lint_theme(ast_program))
    findings.extend(_lint_theme_preference(ast_program))
    findings.extend(_lint_record_types(ast_program, strict=strict))
    findings.extend(lint_functions(ast_program))
    flow_names = {flow.name for flow in ast_program.flows}
    record_names = {record.name for record in ast_program.records}

    try:
        program_ir = lower_program(ast_program)
    except Namel3ssError as err:
        findings.extend(_lint_refs_ast(ast_program, flow_names, record_names))
        findings.append(
            Finding(
                code="lint.parse_failed",
                message="Lowering failed; showing best-effort lint results.",
                line=err.line,
                column=err.column,
                severity="warning",
            )
        )
        return findings

    findings.extend(lint_semantic(program_ir))
    return findings


def lint_project(project: ProjectLoadResult, strict: bool = True) -> list[Finding]:
    findings: list[Finding] = []
    for path, source in project.sources.items():
        for finding in scan_text(source.splitlines()):
            finding.file = path.as_posix()
            findings.append(finding)

    def _tag(findings_list: list[Finding], path: str) -> None:
        for finding in findings_list:
            finding.file = path
        findings.extend(findings_list)

    app_path = project.app_path.as_posix()
    _tag(_lint_reserved_identifiers(project.app_ast), app_path)
    _tag(_lint_theme(project.app_ast), app_path)
    _tag(_lint_theme_preference(project.app_ast), app_path)
    _tag(_lint_record_types(project.app_ast, strict=strict), app_path)
    _tag(lint_functions(project.app_ast), app_path)

    for module in project.modules.values():
        for program, path in zip(module.programs, module.files):
            file_path = path.as_posix()
            _tag(_lint_reserved_identifiers(program), file_path)
            _tag(_lint_record_types(program, strict=strict), file_path)
            _tag(lint_functions(program), file_path)

    findings.extend(lint_semantic(project.program))
    findings.extend(_lint_tool_health(project))
    return findings


def _lint_tool_health(project: ProjectLoadResult) -> list[Finding]:
    report = analyze_tool_health(project)
    app_path = project.app_path.as_posix()
    bindings_file = bindings_path(project.app_path.parent).as_posix()
    findings: list[Finding] = []
    for issue in report.issues:
        file_path = issue.file
        if issue.line is not None:
            file_path = app_path
        elif file_path is None and (
            issue.code.startswith("tools.binding")
            or issue.code.startswith("tools.bindings")
            or issue.code in {
                "tools.invalid_binding",
                "tools.unused_binding",
                "tools.collision",
                "tools.invalid_runner",
                "tools.service_url_missing",
                "tools.container_image_missing",
                "tools.container_runtime_missing",
            }
        ):
            file_path = bindings_file
        findings.append(
            Finding(
                code=issue.code,
                message=issue.message,
                line=issue.line,
                column=issue.column,
                severity=issue.severity,
                file=file_path,
            )
        )
    return findings


def _lint_record_types(ast_program, strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    severity = "error" if strict else "warning"
    for record in ast_program.records:
        for field in record.fields:
            if getattr(field, "type_was_alias", False) and field.raw_type_name:
                findings.append(
                    Finding(
                        code="N3LINT_TYPE_NON_CANONICAL",
                        message=f"Use `{field.type_name}` instead of `{field.raw_type_name}` for field types.",
                        line=field.type_line,
                        column=field.type_column,
                        severity=severity,
                    )
                )
            canonical, was_alias = normalize_type_name(field.type_name)
            if canonical not in {"text", "number", "boolean", "json", "list", "map"}:
                findings.append(
                    Finding(
                        code="N3LINT_UNKNOWN_TYPE",
                        message="Unsupported field type. Allowed: text, number, boolean, json, list, map.",
                        line=field.type_line,
                        column=field.type_column,
                        severity="error",
                    )
                )
    return findings


def _lint_reserved_identifiers(ast_program) -> list[Finding]:
    reserved = set(KEYWORDS.keys())
    findings: list[Finding] = []

    def walk_statements(stmts):
        for stmt in stmts:
            if hasattr(stmt, "body"):
                walk_statements(getattr(stmt, "body"))
            if hasattr(stmt, "then_body"):
                walk_statements(stmt.then_body)
            if hasattr(stmt, "else_body"):
                walk_statements(stmt.else_body)
            if hasattr(stmt, "try_body"):
                walk_statements(stmt.try_body)
            if hasattr(stmt, "catch_body"):
                walk_statements(stmt.catch_body)
            if hasattr(stmt, "cases"):
                for case in stmt.cases:
                    walk_statements(case.body)
            if stmt.__class__.__name__ == "Let":
                if stmt.name in reserved:
                    findings.append(
                        Finding(
                            code="names.reserved_identifier",
                            message=f"Identifier '{stmt.name}' is reserved",
                            line=stmt.line,
                            column=stmt.column,
                        )
                    )

    for flow in ast_program.flows:
        walk_statements(flow.body)
    return findings


def _lint_theme(ast_program) -> list[Finding]:
    allowed = {"light", "dark", "system"}
    value = getattr(ast_program, "app_theme", "system")
    if value not in allowed:
        return [
            Finding(
                code="app.invalid_theme",
                message="Theme must be one of: light, dark, system.",
                line=getattr(ast_program, "app_theme_line", None),
                column=getattr(ast_program, "app_theme_column", None),
                severity="error",
            )
        ]
    token_allowed = {
        "surface": {"default", "raised"},
        "text": {"default", "strong"},
        "muted": {"muted", "subtle"},
        "border": {"default", "strong"},
        "accent": {"primary", "secondary"},
    }
    findings: list[Finding] = []
    pref = getattr(ast_program, "theme_preference", {}) or {}
    persist_val, persist_line, persist_col = pref.get("persist", ("none", None, None))
    if persist_val not in {"none", "local", "file"}:
        findings.append(
            Finding(
                code="app.invalid_theme_persist",
                message="Invalid theme persist value. Allowed: none, local, file.",
                line=persist_line,
                column=persist_col,
                severity="error",
            )
        )
    tokens = getattr(ast_program, "theme_tokens", {}) or {}
    for name, (val, line, col) in tokens.items():
        if name not in token_allowed:
            findings.append(
                Finding(
                    code="app.invalid_theme_token",
                    message="Invalid theme token. Allowed: surface, text, muted, border, accent.",
                    line=line,
                    column=col,
                    severity="error",
                )
            )
            continue
        if val not in token_allowed[name]:
            allowed_vals = ", ".join(sorted(token_allowed[name]))
            findings.append(
                Finding(
                    code="app.invalid_theme_token_value",
                    message=f"Invalid value for token '{name}'. Allowed: {allowed_vals}.",
                    line=line,
                    column=col,
                    severity="error",
                )
            )
    return findings


def _lint_theme_preference(ast_program) -> list[Finding]:
    findings: list[Finding] = []
    pref = getattr(ast_program, "theme_preference", {}) or {}
    persist_val, persist_line, persist_col = pref.get("persist", ("none", None, None))
    allow_override_val, allow_line, allow_col = pref.get("allow_override", (False, None, None))
    if persist_val not in {"none", "local", "file"}:
        findings.append(
            Finding(
                code="app.invalid_theme_persist",
                message="Invalid theme persist value. Allowed: none, local, file.",
                line=persist_line,
                column=persist_col,
                severity="error",
            )
        )
    if not allow_override_val:
        if _flows_contain_theme_change(ast_program.flows):
            findings.append(
                Finding(
                    code="app.theme_override_disabled",
                    message="Theme changes are disabled. Enable app.theme_preference.allow_override is true to allow 'set theme'.",
                    line=allow_line or getattr(ast_program, "app_theme_line", None),
                    column=allow_col or getattr(ast_program, "app_theme_column", None),
                    severity="error",
                )
            )
    return findings


def _flows_contain_theme_change(flows) -> bool:
    def visit(stmt):
        from namel3ss.ast import statements as ast_stmt

        if isinstance(stmt, ast_stmt.ThemeChange):
            return True
        if isinstance(stmt, ast_stmt.If):
            return any(visit(s) for s in stmt.then_body) or any(visit(s) for s in stmt.else_body)
        if isinstance(stmt, ast_stmt.Repeat):
            return any(visit(s) for s in stmt.body)
        if isinstance(stmt, ast_stmt.ForEach):
            return any(visit(s) for s in stmt.body)
        if isinstance(stmt, ast_stmt.Match):
            return any(any(visit(s) for s in c.body) for c in stmt.cases) or (any(visit(s) for s in stmt.otherwise) if stmt.otherwise else False)
        if isinstance(stmt, ast_stmt.TryCatch):
            return any(visit(s) for s in stmt.try_body) or any(visit(s) for s in stmt.catch_body)
        return False

    return any(visit(s) for flow in flows for s in flow.body)


def _lint_refs_ast(ast_program, flow_names: set[str], record_names: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    for page in ast_program.pages:
        for item in page.items:
            if isinstance(item, ast.ButtonItem):
                if item.flow_name not in flow_names:
                    findings.append(
                        Finding(
                            code="refs.unknown_flow",
                            message=f"Button references unknown flow '{item.flow_name}'",
                            line=item.line,
                            column=item.column,
                        )
                    )
            if isinstance(item, ast.FormItem):
                if item.record_name not in record_names:
                    findings.append(
                        Finding(
                            code="refs.unknown_record",
                            message=f"Form references unknown record '{item.record_name}'",
                            line=item.line,
                            column=item.column,
                        )
                    )
            if isinstance(item, ast.TableItem):
                if item.record_name not in record_names:
                    findings.append(
                        Finding(
                            code="refs.unknown_record",
                            message=f"Table references unknown record '{item.record_name}'",
                            line=item.line,
                            column=item.column,
                        )
                    )
                if item.row_actions:
                    for action in item.row_actions:
                        if action.kind == "call_flow" and action.flow_name not in flow_names:
                            findings.append(
                                Finding(
                                    code="refs.unknown_flow",
                                    message=f"Row action references unknown flow '{action.flow_name}'",
                                line=action.line,
                                column=action.column,
                            )
                        )
            if isinstance(item, ast.ListItem):
                if item.record_name not in record_names:
                    findings.append(
                        Finding(
                            code="refs.unknown_record",
                            message=f"List references unknown record '{item.record_name}'",
                            line=item.line,
                            column=item.column,
                        )
                    )
                if item.actions:
                    for action in item.actions:
                        if action.kind == "call_flow" and action.flow_name not in flow_names:
                            findings.append(
                                Finding(
                                    code="refs.unknown_flow",
                                    message=f"List action references unknown flow '{action.flow_name}'",
                                    line=action.line,
                                    column=action.column,
                        )
                    )
            if isinstance(item, ast.ChartItem) and item.record_name:
                if item.record_name not in record_names:
                    findings.append(
                        Finding(
                            code="refs.unknown_record",
                            message=f"Chart references unknown record '{item.record_name}'",
                            line=item.line,
                            column=item.column,
                        )
                    )
            if isinstance(item, ast.ChatItem):
                for child in item.children:
                    if isinstance(child, ast.ChatComposerItem) and child.flow_name not in flow_names:
                        findings.append(
                            Finding(
                                code="refs.unknown_flow",
                                message=f"Composer references unknown flow '{child.flow_name}'",
                                line=child.line,
                                column=child.column,
                            )
                        )
            if isinstance(item, ast.CardItem):
                if item.actions:
                    for action in item.actions:
                        if action.kind == "call_flow" and action.flow_name not in flow_names:
                            findings.append(
                                Finding(
                                    code="refs.unknown_flow",
                                    message=f"Card action references unknown flow '{action.flow_name}'",
                                    line=action.line,
                                    column=action.column,
                                )
                            )
    return findings
