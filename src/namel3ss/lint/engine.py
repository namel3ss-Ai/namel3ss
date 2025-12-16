from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.ir.nodes import lower_program
from namel3ss.lexer.tokens import KEYWORDS
from namel3ss.lint.semantic import lint_semantic
from namel3ss.lint.text_scan import scan_text
from namel3ss.lint.types import Finding
from namel3ss.parser.core import parse
from namel3ss.ast import nodes as ast


def lint_source(source: str) -> list[Finding]:
    lines = source.splitlines()
    findings = scan_text(lines)

    ast_program = None
    try:
        ast_program = parse(source)
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
    return findings
