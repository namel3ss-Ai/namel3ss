from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.expr.common import read_attr_name
from namel3ss.parser.sugar.diagnostics import (
    expected_block_error,
    expected_phrase_error,
    expected_value_error,
)
from namel3ss.parser.sugar.phase2 import (
    ClearStmt,
    NoticeStmt,
    SaveField,
    SaveRecordStmt,
    parse_clear,
    parse_notice,
    parse_save_with,
)
from namel3ss.parser.sugar.phase3 import (
    ParallelVerbAgentEntry,
    ParallelVerbAgentsStmt,
    VerbAgentCallStmt,
    parse_in_parallel,
    parse_verb_agent_call,
)
from namel3ss.parser.sugar.phase4 import AttemptOtherwiseStmt, parse_attempt_otherwise


@dataclass
class StartRunStmt(ast.Statement):
    goal: ast.Expression | None
    memory_pack: str


@dataclass
class PlanWithAgentStmt(ast.Statement):
    agent_name: str
    input_expr: ast.Expression | None


@dataclass
class ReviewParallelStmt(ast.Statement):
    agent_names: List[str]
    target: str


@dataclass
class TimelineEntry(ast.Node):
    stage: str
    detail: ast.Expression | None


@dataclass
class TimelineShowStmt(ast.Statement):
    entries: List[TimelineEntry]


@dataclass
class ComputeOutputHashStmt(ast.Statement):
    pass


@dataclass
class RecordFinalOutputStmt(ast.Statement):
    pass


@dataclass
class IncrementMetricStmt(ast.Statement):
    metric: str


@dataclass
class RecordPolicyViolationStmt(ast.Statement):
    pass


@dataclass
class AttemptBlockedToolStmt(ast.Statement):
    tool_name: str
    argument: ast.Expression


@dataclass
class RequireLatestStmt(ast.Statement):
    record_name: str
    target: str
    message: str


@dataclass
class AccessIndex(ast.Node):
    index: ast.Expression


@dataclass
class AccessAttr(ast.Node):
    name: str


AccessOp = AccessIndex | AccessAttr


@dataclass
class AccessExpr(ast.Expression):
    base: ast.Expression
    ops: List[AccessOp]


@dataclass
class LatestRecordExpr(ast.Expression):
    record_name: str


def parse_start_run(parser) -> StartRunStmt:
    start_tok = parser._advance()
    _expect_ident_value(parser, "a", "start a new run")
    _expect_ident_value(parser, "new", "start a new run")
    parser._expect("RUN", "Expected 'run' after 'start a new'")
    goal_expr = None
    if parser._match("FOR"):
        goal_expr = parser._parse_expression()
    _expect_ident_value(parser, "using", "start a new run using memory pack \"<name>\"")
    parser._expect("MEMORY", "Expected 'memory' after 'using'")
    _expect_ident_value(parser, "pack", "start a new run using memory pack \"<name>\"")
    pack_tok = parser._expect("STRING", "Expected memory pack name string")
    return StartRunStmt(goal=goal_expr, memory_pack=pack_tok.value, line=start_tok.line, column=start_tok.column)


def parse_plan_with(parser) -> PlanWithAgentStmt:
    plan_tok = parser._advance()
    parser._expect("WITH", "Expected 'with' after 'plan'")
    agent_tok = parser._expect("STRING", "Expected agent name string after 'plan with'")
    input_expr = None
    if _match_ident_value(parser, "using"):
        input_expr = parser._parse_expression()
    return PlanWithAgentStmt(agent_name=agent_tok.value, input_expr=input_expr, line=plan_tok.line, column=plan_tok.column)


def parse_review_parallel(parser) -> ReviewParallelStmt:
    review_tok = parser._advance()
    parser._expect("IN", "Expected 'in' after 'review'")
    parser._expect("PARALLEL", "Expected 'parallel' after 'review in'")
    parser._expect("WITH", "Expected 'with' after 'review in parallel'")
    parser._expect("COLON", "Expected ':' after review header")
    parser._expect("NEWLINE", "Expected newline after review header")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise expected_block_error(
            tok,
            label="Review in parallel",
            example='review in parallel with:\n  "critic"\n  "researcher"\nkeep all feedback',
        )
    agents: List[str] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name_tok = parser._expect("STRING", "Expected agent name string")
        agents.append(name_tok.value)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of review block")
    if not agents:
        tok = parser._current()
        raise expected_value_error(
            tok,
            label="Review agent list",
            example='review in parallel with:\n  "critic"\n  "researcher"\nkeep all feedback',
        )
    while parser._match("NEWLINE"):
        pass
    _expect_ident_value(parser, "keep", "keep all feedback")
    _expect_ident_value(parser, "all", "keep all feedback")
    target_tok = parser._expect("IDENT", "Expected name after 'keep all'")
    return ReviewParallelStmt(agent_names=agents, target=target_tok.value, line=review_tok.line, column=review_tok.column)


def parse_timeline_show(parser) -> TimelineShowStmt:
    timeline_tok = parser._advance()
    _expect_ident_value(parser, "shows", "timeline shows:")
    parser._expect("COLON", "Expected ':' after timeline shows")
    parser._expect("NEWLINE", "Expected newline after timeline shows")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise expected_block_error(
            tok,
            label="Timeline",
            example='timeline shows:\n  Start: goal\n  Memory: "agent-minimal"',
        )
    entries: List[TimelineEntry] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        stage_tok = parser._current()
        if stage_tok.type == "STRING":
            parser._advance()
            stage = stage_tok.value
        elif stage_tok.type == "IDENT":
            parser._advance()
            stage = stage_tok.value
        else:
            raise Namel3ssError("Expected timeline stage label", line=stage_tok.line, column=stage_tok.column)
        detail_expr = None
        if parser._match("COLON"):
            if parser._current().type in {"NEWLINE", "DEDENT"}:
                tok = parser._current()
                raise expected_value_error(
                    tok,
                    label="Timeline entry detail",
                    example='timeline shows:\n  Start: goal',
                )
            detail_expr = parser._parse_expression()
        entries.append(TimelineEntry(stage=stage, detail=detail_expr, line=stage_tok.line, column=stage_tok.column))
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of timeline block")
    while parser._match("NEWLINE"):
        pass
    if not entries:
        tok = parser._current()
        raise expected_value_error(
            tok,
            label="Timeline entries",
            example='timeline shows:\n  Start: goal',
        )
    return TimelineShowStmt(entries=entries, line=timeline_tok.line, column=timeline_tok.column)


def parse_compute_output_hash(parser) -> ComputeOutputHashStmt:
    compute_tok = parser._advance()
    _expect_ident_value(parser, "output", "compute output hash")
    _expect_ident_value(parser, "hash", "compute output hash")
    return ComputeOutputHashStmt(line=compute_tok.line, column=compute_tok.column)


def parse_record_final_output(parser) -> RecordFinalOutputStmt:
    record_tok = parser._advance()
    _expect_ident_value(parser, "final", "record final output")
    _expect_ident_value(parser, "output", "record final output")
    return RecordFinalOutputStmt(line=record_tok.line, column=record_tok.column)


def parse_increment_metric(parser) -> IncrementMetricStmt:
    inc_tok = parser._advance()
    metric_tok = parser._current()
    if metric_tok.type in {"AI", "TOOL", "IDENT"}:
        parser._advance()
    else:
        raise Namel3ssError("Expected metric name after 'increment'", line=metric_tok.line, column=metric_tok.column)
    if not parser._match("CALLS") and not _match_ident_value(parser, "calls"):
        tok = parser._current()
        raise expected_phrase_error(tok, phrase="calls", example="increment ai calls")
    if metric_tok.type == "AI" or metric_tok.value == "ai":
        metric = "ai_calls"
    elif metric_tok.type == "TOOL" or metric_tok.value == "tool":
        metric = "tool_calls"
    else:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown metric '{metric_tok.value}'.",
                why="Metrics sugar only supports ai calls or tool calls.",
                fix="Use `increment ai calls` or `increment tool calls`.",
                example="increment ai calls",
            ),
            line=metric_tok.line,
            column=metric_tok.column,
        )
    return IncrementMetricStmt(metric=metric, line=inc_tok.line, column=inc_tok.column)


def parse_record_policy_violation(parser) -> RecordPolicyViolationStmt:
    record_tok = parser._advance()
    _expect_ident_value(parser, "policy", "record policy violation")
    _expect_ident_value(parser, "violation", "record policy violation")
    return RecordPolicyViolationStmt(line=record_tok.line, column=record_tok.column)


def parse_attempt_blocked_tool(parser) -> AttemptBlockedToolStmt:
    attempt_tok = parser._advance()
    tool_name = _read_phrase_until_string(parser)
    if parser._current().type != "STRING":
        tok = parser._current()
        raise expected_value_error(
            tok,
            label="Tool argument",
            example='attempt unsafe request "https://example.com/"\nexpect blocked by policy',
        )
    argument = parser._parse_expression()
    while parser._match("NEWLINE"):
        pass
    expect_tok = parser._current()
    if not _match_ident_value(parser, "expect"):
        raise expected_phrase_error(
            expect_tok,
            phrase="expect blocked by policy",
            example='attempt unsafe request "https://example.com/"\nexpect blocked by policy',
        )
    _expect_ident_value(parser, "blocked", "expect blocked by policy")
    _expect_ident_value(parser, "by", "expect blocked by policy")
    _expect_ident_value(parser, "policy", "expect blocked by policy")
    return AttemptBlockedToolStmt(
        tool_name=tool_name,
        argument=argument,
        line=attempt_tok.line,
        column=attempt_tok.column,
    )


def parse_require_latest(parser) -> RequireLatestStmt:
    require_tok = parser._advance()
    parser._expect("LATEST", "Expected 'latest' after 'require'")
    record_tok = parser._expect("STRING", "Expected record name after 'require latest'")
    parser._expect("AS", "Expected 'as' after record name")
    target_tok = parser._expect("IDENT", "Expected name after 'as'")
    parser._expect("OTHERWISE", "Expected 'otherwise' after required record binding")
    message_tok = parser._expect("STRING", "Expected message after 'otherwise'")
    return RequireLatestStmt(
        record_name=record_tok.value,
        target=target_tok.value,
        message=message_tok.value,
        line=require_tok.line,
        column=require_tok.column,
    )


def parse_latest_expr(parser) -> LatestRecordExpr:
    latest_tok = parser._advance()
    record_tok = parser._expect("STRING", "Expected record name after 'latest'")
    return LatestRecordExpr(record_name=record_tok.value, line=latest_tok.line, column=latest_tok.column)


def parse_postfix_access(parser, base: ast.Expression) -> ast.Expression:
    if parser._current().type != "LBRACKET":
        return base
    ops: List[AccessOp] = []
    while parser._match("LBRACKET"):
        if parser._current().type in {"RBRACKET", "NEWLINE", "DEDENT"}:
            tok = parser._current()
            raise Namel3ssError("Expected list index expression", line=tok.line, column=tok.column)
        index_expr = parser._parse_expression()
        parser._expect("RBRACKET", "Expected ']' after index expression")
        ops.append(AccessIndex(index=index_expr, line=index_expr.line, column=index_expr.column))
        while parser._match("DOT"):
            dot_tok = parser.tokens[parser.position - 1]
            name = read_attr_name(parser, context="identifier after '.'")
            ops.append(AccessAttr(name=name, line=dot_tok.line, column=dot_tok.column))
        if parser._current().type != "LBRACKET":
            break
    return AccessExpr(base=base, ops=ops, line=base.line, column=base.column)


def _read_phrase_until_string(parser) -> str:
    tokens = []
    while True:
        tok = parser._current()
        if tok.type == "STRING":
            break
        if tok.type in {"NEWLINE", "INDENT", "DEDENT"}:
            raise Namel3ssError("Expected tool name before argument", line=tok.line, column=tok.column)
        tokens.append(tok)
        parser._advance()
    if not tokens:
        tok = parser._current()
        raise Namel3ssError("Expected tool name before argument", line=tok.line, column=tok.column)
    return _phrase_text(tokens)


def _phrase_text(tokens) -> str:
    parts: List[str] = []
    for tok in tokens:
        if tok.type == "DOT":
            if parts:
                parts[-1] = f"{parts[-1]}."
            else:
                parts.append(".")
            continue
        value = tok.value
        if value is None:
            continue
        parts.append(str(value))
    return " ".join(parts).strip()


def _match_ident_value(parser, value: str) -> bool:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return True
    return False


def _expect_ident_value(parser, value: str, example: str) -> None:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return
    raise expected_phrase_error(tok, phrase=value, example=example)


__all__ = [
    "AccessAttr",
    "AccessExpr",
    "AccessIndex",
    "AttemptBlockedToolStmt",
    "ComputeOutputHashStmt",
    "IncrementMetricStmt",
    "LatestRecordExpr",
    "PlanWithAgentStmt",
    "RecordFinalOutputStmt",
    "RecordPolicyViolationStmt",
    "ReviewParallelStmt",
    "RequireLatestStmt",
    "StartRunStmt",
    "TimelineEntry",
    "TimelineShowStmt",
    "parse_attempt_blocked_tool",
    "parse_compute_output_hash",
    "parse_increment_metric",
    "parse_latest_expr",
    "parse_plan_with",
    "parse_record_final_output",
    "parse_record_policy_violation",
    "parse_review_parallel",
    "parse_require_latest",
    "parse_start_run",
    "parse_timeline_show",
    "parse_postfix_access",
]
