from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar import phase3 as sugar
from namel3ss.parser.sugar.lowering.expressions import _lower_expression


def _lower_verb_agent_call(stmt: sugar.VerbAgentCallStmt) -> list[ast.Statement]:
    return [
        ast.RunAgentStmt(
            agent_name=stmt.agent_name,
            input_expr=_lower_expression(stmt.input_expr),
            target=stmt.target,
            line=stmt.line,
            column=stmt.column,
        )
    ]


def _lower_parallel_verb_agents(stmt: sugar.ParallelVerbAgentsStmt) -> list[ast.Statement]:
    entries = [
        ast.ParallelAgentEntry(
            agent_name=entry.agent_name,
            input_expr=_lower_expression(entry.input_expr),
            line=entry.line,
            column=entry.column,
        )
        for entry in stmt.entries
    ]
    merge = ast.AgentMergePolicy(
        policy=stmt.policy,
        require_keys=None,
        require_non_empty=None,
        score_key=None,
        score_rule=None,
        min_consensus=None,
        consensus_key=None,
        line=stmt.policy_line if stmt.policy_line is not None else stmt.line,
        column=stmt.policy_column if stmt.policy_column is not None else stmt.column,
    )
    return [
        ast.RunAgentsParallelStmt(
            entries=entries,
            target=stmt.target,
            merge=merge,
            line=stmt.line,
            column=stmt.column,
        )
    ]


__all__ = ["_lower_parallel_verb_agents", "_lower_verb_agent_call"]
