from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable

from namel3ss.ir import nodes as ir
from namel3ss.runtime.records.state_paths import record_state_path


_QUESTION_WORDS = ("which", "what", "why", "how", "lowest", "highest", "top", "most", "least")
_MAX_QUESTION_LENGTH = 400
_EMPTY_CONTEXT_MARKERS = (
    "(none found)",
    "no records found",
    "no orders found",
    "no data found",
    "0 records",
    "0 orders",
)


@dataclass
class ExprInfo:
    var_refs: set[str] = field(default_factory=set)
    state_refs: set[tuple[str, ...]] = field(default_factory=set)
    literal_texts: list[str] = field(default_factory=list)
    has_tool_call: bool = False
    has_function_call: bool = False
    input_ref: bool = False


@dataclass
class AssignmentInfo:
    target_kind: str
    target: str | tuple[str, ...]
    expr_info: ExprInfo


def collect_ai_context_diagnostics(program: ir.Program) -> list[dict]:
    diagnostics: list[dict] = []
    for flow in program.flows:
        diagnostics.extend(_analyze_flow(flow))
    diagnostics.sort(key=lambda item: (item.get("flow") or "", item.get("line") or 0, item.get("column") or 0))
    return diagnostics


def collect_runtime_ai_context_diagnostics(traces: Iterable[dict]) -> list[dict]:
    traces_list = [trace for trace in traces if isinstance(trace, dict)]
    if not traces_list:
        return []
    if not _has_data_usage(traces_list):
        return []
    latest_match = None
    for trace in traces_list:
        if not _is_ai_trace(trace):
            continue
        input_text = trace.get("input")
        if not isinstance(input_text, str):
            continue
        if len(input_text) > _MAX_QUESTION_LENGTH:
            continue
        if not _text_looks_question_like(input_text):
            continue
        if _has_context_markers(input_text):
            continue
        latest_match = trace
    if not latest_match:
        return []
    return [
        {
            "id": "AI_CONTEXT_LIKELY_MISSING",
            "category": "AI Design Warning",
            "severity": "warning",
            "message": "This AI call looks like a data question, but the AI input is mostly the question text.",
            "hint": "Include a compact summary of relevant records/tool output in the AI prompt.",
            "source": "runtime",
        }
    ]


def _analyze_flow(flow: ir.Flow) -> list[dict]:
    results_vars: set[str] = set()
    tool_output_vars: set[str] = set()
    tool_output_state_paths: set[tuple[str, ...]] = set()
    assignments: list[AssignmentInfo] = []
    ask_ai: list[ir.AskAIStmt] = []

    for stmt in _walk_statements(flow.body):
        if isinstance(stmt, ir.Find):
            result_name = _results_name(stmt.record_name)
            if result_name:
                results_vars.add(result_name)
        elif isinstance(stmt, ir.AskAIStmt):
            ask_ai.append(stmt)
        elif isinstance(stmt, ir.Let):
            info = _collect_expr_info(stmt.expression)
            assignments.append(AssignmentInfo("var", stmt.name, info))
            if info.has_tool_call or info.has_function_call:
                tool_output_vars.add(stmt.name)
        elif isinstance(stmt, ir.Set):
            info = _collect_expr_info(stmt.expression)
            if isinstance(stmt.target, ir.VarReference):
                assignments.append(AssignmentInfo("var", stmt.target.name, info))
                if info.has_tool_call or info.has_function_call:
                    tool_output_vars.add(stmt.target.name)
            elif isinstance(stmt.target, ir.StatePath):
                target_path = tuple(stmt.target.path)
                assignments.append(AssignmentInfo("state", target_path, info))
                if info.has_tool_call or info.has_function_call:
                    tool_output_state_paths.add(target_path)

    if not results_vars:
        return []

    derived_vars: set[str] = set()
    derived_state_paths: set[tuple[str, ...]] = set()
    context_vars = set(results_vars) | set(tool_output_vars)
    context_state_paths = set(tool_output_state_paths)

    changed = True
    while changed:
        changed = False
        for assignment in assignments:
            if assignment.target_kind == "var":
                if assignment.target in derived_vars or assignment.target in context_vars:
                    continue
            if assignment.target_kind == "state":
                if assignment.target in derived_state_paths or assignment.target in context_state_paths:
                    continue
            if _expr_references_context(assignment.expr_info, context_vars, context_state_paths, derived_vars, derived_state_paths):
                if assignment.target_kind == "var":
                    derived_vars.add(str(assignment.target))
                else:
                    derived_state_paths.add(tuple(assignment.target))
                changed = True

    context_vars.update(derived_vars)
    context_state_paths.update(derived_state_paths)

    diagnostics: list[dict] = []
    for stmt in ask_ai:
        info = _collect_expr_info(stmt.input_expr)
        if not _expr_looks_question_like(info):
            continue
        if info.has_tool_call or info.has_function_call:
            continue
        if _expr_references_context(info, context_vars, context_state_paths, derived_vars, derived_state_paths):
            continue
        diagnostics.append(
            {
                "id": "AI_CONTEXT_MISSING",
                "category": "AI Design Warning",
                "severity": "warning",
                "message": "AI input may not include app data. You query data in this flow but don't pass it into Ask AI.",
                "hint": "Build a compact context string from your query results and prepend it to the question.",
                "flow": flow.name,
                "line": stmt.line,
                "column": stmt.column,
                "source": "static",
            }
        )
    return diagnostics


def _results_name(record_name: str) -> str:
    path = record_state_path(record_name)
    if not path:
        return ""
    return f"{'_'.join(path)}_results"


def _walk_statements(statements: Iterable[ir.Statement]) -> Iterable[ir.Statement]:
    for stmt in statements:
        yield stmt
        if isinstance(stmt, ir.If):
            yield from _walk_statements(stmt.then_body)
            yield from _walk_statements(stmt.else_body)
        elif isinstance(stmt, ir.ForEach):
            yield from _walk_statements(stmt.body)
        elif isinstance(stmt, ir.Repeat):
            yield from _walk_statements(stmt.body)
        elif isinstance(stmt, ir.RepeatWhile):
            yield from _walk_statements(stmt.body)
        elif isinstance(stmt, ir.Match):
            for case in stmt.cases:
                yield from _walk_statements(case.body)
            if stmt.otherwise:
                yield from _walk_statements(stmt.otherwise)
        elif isinstance(stmt, ir.TryCatch):
            yield from _walk_statements(stmt.try_body)
            yield from _walk_statements(stmt.catch_body)
        elif isinstance(stmt, ir.ParallelBlock):
            for task in stmt.tasks:
                yield from _walk_statements(task.body)


def _collect_expr_info(expr: ir.Expression) -> ExprInfo:
    info = ExprInfo()

    def _walk(value: ir.Expression) -> None:
        if isinstance(value, ir.Literal):
            if isinstance(value.value, str):
                info.literal_texts.append(value.value)
            return
        if isinstance(value, ir.VarReference):
            info.var_refs.add(value.name)
            return
        if isinstance(value, ir.AttrAccess):
            info.var_refs.add(value.base)
            if value.base == "input":
                info.input_ref = True
            return
        if isinstance(value, ir.StatePath):
            path = tuple(value.path)
            info.state_refs.add(path)
            if value.path and value.path[0] == "input":
                info.input_ref = True
            return
        if isinstance(value, ir.ToolCallExpr):
            info.has_tool_call = True
            for arg in value.arguments:
                _walk(arg.value)
            return
        if isinstance(value, ir.CallFunctionExpr):
            info.has_function_call = True
            for arg in value.arguments:
                _walk(arg.value)
            return
        if isinstance(value, ir.UnaryOp):
            _walk(value.operand)
            return
        if isinstance(value, (ir.BinaryOp, ir.Comparison)):
            _walk(value.left)
            _walk(value.right)
            return
        if isinstance(value, ir.ListExpr):
            for item in value.items:
                _walk(item)
            return
        if isinstance(value, ir.MapExpr):
            for entry in value.entries:
                _walk(entry.key)
                _walk(entry.value)
            return
        if isinstance(value, ir.ListOpExpr):
            _walk(value.target)
            if value.value is not None:
                _walk(value.value)
            if value.index is not None:
                _walk(value.index)
            return
        if isinstance(value, ir.MapOpExpr):
            _walk(value.target)
            if value.key is not None:
                _walk(value.key)
            if value.value is not None:
                _walk(value.value)
            return

    _walk(expr)
    return info


def _expr_looks_question_like(info: ExprInfo) -> bool:
    if info.input_ref:
        return True
    for name in info.var_refs:
        if _name_looks_question_like(name):
            return True
    for text in info.literal_texts:
        if _text_looks_question_like(text):
            return True
    return False


def _name_looks_question_like(name: str) -> bool:
    lower = name.lower()
    return "question" in lower or "query" in lower or "prompt" in lower


def _text_looks_question_like(text: str) -> bool:
    cleaned = text.strip().lower()
    if not cleaned:
        return False
    if "?" in cleaned:
        return True
    for word in _QUESTION_WORDS:
        if cleaned.startswith(f"{word} "):
            return True
    return any(word in cleaned for word in _QUESTION_WORDS)


def _expr_references_context(
    info: ExprInfo,
    context_vars: set[str],
    context_state_paths: set[tuple[str, ...]],
    derived_vars: set[str],
    derived_state_paths: set[tuple[str, ...]],
) -> bool:
    if info.var_refs.intersection(context_vars | derived_vars):
        return True
    if info.state_refs.intersection(context_state_paths | derived_state_paths):
        return True
    return False


def _is_ai_trace(trace: dict) -> bool:
    return bool(trace.get("ai_name") or trace.get("ai_profile_name"))


def _has_data_usage(traces: list[dict]) -> bool:
    for trace in traces:
        if trace.get("type") in {"tool_call", "tool_call_requested", "tool_call_completed", "tool_call_failed"}:
            return True
        if trace.get("tool_calls") or trace.get("tool_results"):
            return True
        if trace.get("record") or trace.get("record_name"):
            return True
        events = trace.get("canonical_events")
        if isinstance(events, list) and any(event.get("type", "").startswith("tool_call") for event in events if isinstance(event, dict)):
            return True
    return False


def _has_context_markers(text: str) -> bool:
    lower = text.lower()
    if any(marker in lower for marker in _EMPTY_CONTEXT_MARKERS):
        return True
    if re.search(r"\\brecords?\\s*:", lower):
        return True
    if re.search(r"\\bdata\\s*:", lower):
        return True
    if re.search(r"\\bn\\s*=\\s*\\d+", lower):
        return True
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if sum(1 for line in lines if line.startswith(("-", "*"))) >= 2:
        return True
    return False
