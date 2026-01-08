from __future__ import annotations

from namel3ss.ir import nodes as ir
from namel3ss.lint.types import Finding


def lint_agent_orchestration(program: ir.Program) -> list[Finding]:
    findings: list[Finding] = []

    def walk(stmts: list[ir.Statement]) -> None:
        for stmt in stmts:
            if isinstance(stmt, ir.RunAgentsParallelStmt):
                _lint_parallel_stmt(stmt, findings)
                continue
            if isinstance(stmt, ir.If):
                walk(stmt.then_body)
                walk(stmt.else_body)
            elif isinstance(stmt, ir.Repeat):
                walk(stmt.body)
            elif isinstance(stmt, ir.RepeatWhile):
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
            elif isinstance(stmt, ir.ParallelBlock):
                for task in stmt.tasks:
                    walk(task.body)

    for flow in program.flows:
        walk(flow.body)

    return findings


def _lint_parallel_stmt(stmt: ir.RunAgentsParallelStmt, findings: list[Finding]) -> None:
    if len(stmt.entries) > 3:
        findings.append(
            Finding(
                code="agents.parallel_limit",
                message="Parallel agent limit exceeded (max 3).",
                line=stmt.line,
                column=stmt.column,
            )
        )
    merge = stmt.merge
    if merge is None:
        return
    policy = merge.policy
    if policy not in {"first_valid", "ranked", "consensus", "all"}:
        findings.append(
            Finding(
                code="agents.merge_policy_invalid",
                message=f"Unknown merge policy '{policy}'.",
                line=merge.line,
                column=merge.column,
            )
        )
        return
    if policy == "ranked" and not (merge.score_key or merge.score_rule):
        findings.append(
            Finding(
                code="agents.merge_score_missing",
                message="Merge policy 'ranked' requires score_key or score_rule.",
                line=merge.line,
                column=merge.column,
            )
        )
    if policy == "ranked" and merge.score_key and merge.score_rule:
        findings.append(
            Finding(
                code="agents.merge_score_conflict",
                message="Merge policy 'ranked' may not set both score_key and score_rule.",
                line=merge.line,
                column=merge.column,
            )
        )
    if policy == "ranked" and merge.score_rule and merge.score_rule not in {"text_length"}:
        findings.append(
            Finding(
                code="agents.merge_score_rule_invalid",
                message=f"Merge policy 'ranked' does not support score_rule '{merge.score_rule}'.",
                line=merge.line,
                column=merge.column,
            )
        )
    if policy == "consensus":
        if not isinstance(merge.min_consensus, int) or merge.min_consensus <= 0:
            findings.append(
                Finding(
                    code="agents.merge_consensus_missing",
                    message="Merge policy 'consensus' requires min_consensus.",
                    line=merge.line,
                    column=merge.column,
                )
            )
        elif merge.min_consensus > len(stmt.entries):
            findings.append(
                Finding(
                    code="agents.merge_consensus_unreachable",
                    message="Consensus threshold exceeds candidate count.",
                    line=merge.line,
                    column=merge.column,
                )
            )


__all__ = ["lint_agent_orchestration"]
