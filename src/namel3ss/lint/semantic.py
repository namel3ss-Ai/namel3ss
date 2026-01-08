from __future__ import annotations

from typing import List, Set

from namel3ss.ir import nodes as ir
from namel3ss.agents.orchestration.lint import lint_agent_orchestration
from namel3ss.lint.types import Finding


def lint_semantic(program_ir: ir.Program) -> List[Finding]:
    findings: List[Finding] = []
    flow_names: Set[str] = {flow.name for flow in program_ir.flows}
    record_names: Set[str] = {record.name for record in program_ir.records}
    for page in program_ir.pages:
        for item in page.items:
            if isinstance(item, ir.ButtonItem):
                if item.flow_name not in flow_names:
                    findings.append(
                        Finding(
                            code="refs.unknown_flow",
                            message=f"Button references unknown flow '{item.flow_name}'",
                            line=item.line,
                            column=item.column,
                        )
                    )
            if isinstance(item, ir.FormItem):
                if item.record_name not in record_names:
                    findings.append(
                        Finding(
                            code="refs.unknown_record",
                            message=f"Form references unknown record '{item.record_name}'",
                            line=item.line,
                            column=item.column,
                        )
                    )
            if isinstance(item, ir.TableItem):
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
            if isinstance(item, ir.ListItem):
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
            if isinstance(item, ir.CardItem):
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
            if isinstance(item, ir.ChartItem) and item.record_name:
                if item.record_name not in record_names:
                    findings.append(
                        Finding(
                            code="refs.unknown_record",
                            message=f"Chart references unknown record '{item.record_name}'",
                            line=item.line,
                            column=item.column,
                        )
                    )
            if isinstance(item, ir.ChatItem):
                for child in item.children:
                    if isinstance(child, ir.ChatComposerItem) and child.flow_name not in flow_names:
                        findings.append(
                            Finding(
                                code="refs.unknown_flow",
                                message=f"Composer references unknown flow '{child.flow_name}'",
                                line=child.line,
                                column=child.column,
                            )
                        )
    findings.extend(_lint_legacy_save(program_ir.flows))
    findings.extend(lint_agent_orchestration(program_ir))
    return findings


def _lint_legacy_save(flows: list[ir.Flow]) -> List[Finding]:
    findings: List[Finding] = []

    def walk(stmts: list[ir.Statement]):
        for stmt in stmts:
            if isinstance(stmt, ir.Save):
                findings.append(
                    Finding(
                        code="N3LINT_SAVE_LEGACY",
                        message='Prefer `create "Record" with <values> as <var>` over legacy `save Record`.',
                        line=stmt.line,
                        column=stmt.column,
                        severity="warning",
                    )
                )
                continue
            if isinstance(stmt, ir.If):
                walk(stmt.then_body)
                walk(stmt.else_body)
            elif isinstance(stmt, ir.Repeat):
                walk(stmt.body)
            elif isinstance(stmt, ir.ForEach):
                walk(stmt.body)
            elif isinstance(stmt, ir.Match):
                for case in stmt.cases:
                    walk(case.body)
                if stmt.otherwise:
                    walk(stmt.otherwise)
            elif isinstance(stmt, ir.TryCatch):
                walk(stmt.try_body)
                walk(stmt.catch_body)

    for flow in flows:
        walk(flow.body)
    return findings
