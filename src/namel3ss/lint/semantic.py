from __future__ import annotations

from typing import List, Set

from namel3ss.ir import nodes as ir
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
    return findings
