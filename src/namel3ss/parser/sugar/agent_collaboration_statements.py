from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.core.helpers import parse_reference_name
from namel3ss.parser.stmt.run_agent import _validate_merge_policy
from namel3ss.parser.sugar.diagnostics import expected_block_error, expected_phrase_error, expected_value_error


_ALLOWED_VERBS = {
    "drafts",
    "plans",
    "reviews",
    "critiques",
    "researches",
    "enriches",
    "summarizes",
    "answers",
}


@dataclass
class VerbAgentCallStmt(ast.Statement):
    agent_name: str
    verb: str
    input_expr: ast.Expression
    target: str


@dataclass
class ParallelVerbAgentEntry(ast.Node):
    agent_name: str
    verb: str
    input_expr: ast.Expression
    target: str


@dataclass
class ParallelVerbAgentsStmt(ast.Statement):
    entries: List[ParallelVerbAgentEntry]
    policy: str
    target: str
    policy_line: int | None = None
    policy_column: int | None = None


def parse_verb_agent_call(parser) -> VerbAgentCallStmt:
    name_tok, agent_name = _parse_agent_name(parser)
    verb_tok = parser._expect("IDENT", "Expected agent verb after agent name")
    verb = verb_tok.value
    if not _is_allowed_verb(verb):
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown agent verb '{verb}'.",
                why="Agent verb calls use a fixed set of verbs.",
                fix=f"Use one of: {', '.join(sorted(_ALLOWED_VERBS))}.",
                example='planner drafts goal as plan',
            ),
            line=verb_tok.line,
            column=verb_tok.column,
        )
    if parser._current().type in {"NEWLINE", "DEDENT"}:
        tok = parser._current()
        raise expected_value_error(
            tok,
            label="Agent input",
            example='planner drafts goal as plan',
        )
    input_expr = parser._parse_expression()
    parser._expect("AS", "Expected 'as' to bind agent result")
    target_tok = parser._expect("IDENT", "Expected target identifier after 'as'")
    return VerbAgentCallStmt(
        agent_name=agent_name,
        verb=verb,
        input_expr=input_expr,
        target=target_tok.value,
        line=name_tok.line,
        column=name_tok.column,
    )


def parse_in_parallel(parser) -> ParallelVerbAgentsStmt:
    in_tok = parser._advance()
    parser._expect("PARALLEL", "Expected 'parallel' after 'in'")
    parser._expect("COLON", "Expected ':' after in parallel")
    parser._expect("NEWLINE", "Expected newline after in parallel")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise expected_block_error(
            tok,
            label="In parallel",
            example='in parallel:\n  critic reviews plan as critic_text',
        )
    entries: List[ParallelVerbAgentEntry] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        entries.append(_parse_parallel_entry(parser))
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of in parallel block")
    if not entries:
        tok = parser._current()
        raise expected_value_error(
            tok,
            label="Parallel agent list",
            example='in parallel:\n  critic reviews plan as critic_text',
        )
    while parser._match("NEWLINE"):
        pass
    policy, policy_tok, target = _parse_merge_policy_line(parser)
    _validate_merge_policy(policy, policy_tok, score_key=None, score_rule=None, min_consensus=None)
    return ParallelVerbAgentsStmt(
        entries=entries,
        policy=policy,
        target=target,
        policy_line=policy_tok.line,
        policy_column=policy_tok.column,
        line=in_tok.line,
        column=in_tok.column,
    )


def _parse_parallel_entry(parser) -> ParallelVerbAgentEntry:
    name_tok, agent_name = _parse_agent_name(parser)
    verb_tok = parser._expect("IDENT", "Expected agent verb after agent name")
    verb = verb_tok.value
    if not _is_allowed_verb(verb):
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown agent verb '{verb}'.",
                why="Agent verb calls use a fixed set of verbs.",
                fix=f"Use one of: {', '.join(sorted(_ALLOWED_VERBS))}.",
                example='critic reviews plan as critique',
            ),
            line=verb_tok.line,
            column=verb_tok.column,
        )
    if parser._current().type in {"NEWLINE", "DEDENT"}:
        tok = parser._current()
        raise expected_value_error(
            tok,
            label="Agent input",
            example='critic reviews plan as critique',
        )
    input_expr = parser._parse_expression()
    parser._expect("AS", "Expected 'as' to bind agent result")
    target_tok = parser._expect("IDENT", "Expected target identifier after 'as'")
    return ParallelVerbAgentEntry(
        agent_name=agent_name,
        verb=verb,
        input_expr=input_expr,
        target=target_tok.value,
        line=name_tok.line,
        column=name_tok.column,
    )


def _parse_agent_name(parser):
    if parser._match("AGENT"):
        name_tok = parser._current()
        agent_name = parse_reference_name(parser, context="agent")
        return name_tok, agent_name
    name_tok = parser._current()
    agent_name = parse_reference_name(parser, context="agent")
    return name_tok, agent_name


def _parse_merge_policy_line(parser):
    merge_tok = parser._current()
    if not _match_ident_value(parser, "merge"):
        raise expected_phrase_error(
            merge_tok,
            phrase="merge policy is \"<policy>\" as <name>",
            example='merge policy is "all" as feedback',
        )
    _expect_ident_value(parser, "policy", "merge policy is \"<policy>\" as <name>")
    parser._expect("IS", "Expected 'is' after merge policy")
    policy_tok = parser._expect("STRING", "Expected merge policy string")
    parser._expect("AS", "Expected 'as' after merge policy")
    target_tok = parser._expect("IDENT", "Expected target identifier after 'as'")
    parser._match("NEWLINE")
    return policy_tok.value, policy_tok, target_tok.value


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


def _is_allowed_verb(verb: str | None) -> bool:
    return bool(verb) and verb in _ALLOWED_VERBS


def is_allowed_verb(verb: str | None) -> bool:
    return _is_allowed_verb(verb)


__all__ = [
    "ParallelVerbAgentEntry",
    "ParallelVerbAgentsStmt",
    "VerbAgentCallStmt",
    "is_allowed_verb",
    "parse_in_parallel",
    "parse_verb_agent_call",
]
