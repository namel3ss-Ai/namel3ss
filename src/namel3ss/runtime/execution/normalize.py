from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from namel3ss.ir import nodes as ir

from .graph import ExplanationGraph

SKIP_KINDS = {"branch_skipped", "case_skipped", "otherwise_skipped", "catch_skipped"}


def normalize_graph(graph: ExplanationGraph) -> ExplanationGraph:
    nodes = sorted(graph.nodes, key=lambda node: node.id)
    edges = sorted(graph.edges, key=lambda edge: (edge.src, edge.dst, edge.kind, edge.note))
    summary = _normalize_dict(graph.summary)
    return ExplanationGraph(nodes=nodes, edges=edges, summary=summary)


def stable_join(items: list[str], sep: str = ", ") -> str:
    return sep.join(items)


def stable_bullets(lines: list[str]) -> list[str]:
    return [line if line.startswith("- ") else f"- {line}" for line in lines]


def stable_truncate(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def summarize_value(value: object, limit: int = 80) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, str):
        return stable_truncate(value, limit=limit)
    if value is None:
        return "null"
    if isinstance(value, list):
        count = len(value)
        return f"list with {count} items"
    if isinstance(value, dict):
        count = len(value)
        return f"object with {count} keys"
    return type(value).__name__


def format_expression(expr: ir.Expression) -> str:
    if isinstance(expr, ir.Literal):
        return _format_literal(expr.value)
    if isinstance(expr, ir.VarReference):
        return expr.name
    if isinstance(expr, ir.AttrAccess):
        return ".".join([expr.base, *expr.attrs])
    if isinstance(expr, ir.StatePath):
        return "state." + ".".join(expr.path)
    if isinstance(expr, ir.UnaryOp):
        return f"{expr.op} {format_expression(expr.operand)}"
    if isinstance(expr, ir.BinaryOp):
        return f"{format_expression(expr.left)} {expr.op} {format_expression(expr.right)}"
    if isinstance(expr, ir.Comparison):
        op = _comparison_op(expr.kind)
        return f"{format_expression(expr.left)} {op} {format_expression(expr.right)}"
    if isinstance(expr, ir.ToolCallExpr):
        return f"call tool {expr.tool_name}"
    if isinstance(expr, ir.CallFunctionExpr):
        return f"call function {expr.function_name}"
    if isinstance(expr, ir.ListExpr):
        return f"list with {len(expr.items)} items"
    if isinstance(expr, ir.MapExpr):
        return f"map with {len(expr.entries)} entries"
    if isinstance(expr, ir.ListOpExpr):
        target = format_expression(expr.target)
        if expr.kind == "length":
            return f"list length of {target}"
        if expr.kind == "append":
            value = format_expression(expr.value) if expr.value is not None else "value"
            return f"list append {target} with {value}"
        if expr.kind == "get":
            index = format_expression(expr.index) if expr.index is not None else "index"
            return f"list get {target} at {index}"
    if isinstance(expr, ir.MapOpExpr):
        target = format_expression(expr.target)
        if expr.kind == "get":
            key = format_expression(expr.key) if expr.key is not None else "key"
            return f"map get {target} key {key}"
        if expr.kind == "set":
            key = format_expression(expr.key) if expr.key is not None else "key"
            value = format_expression(expr.value) if expr.value is not None else "value"
            return f"map set {target} key {key} value {value}"
        if expr.kind == "keys":
            return f"map keys of {target}"
    return "expression"


def format_assignable(target: ir.Assignable) -> str:
    if isinstance(target, ir.VarReference):
        return target.name
    if isinstance(target, ir.StatePath):
        return "state." + ".".join(target.path)
    return "target"


def build_plain_text(pack: dict) -> str:
    lines: list[str] = []
    summary = pack.get("summary") or ""
    flow_name = pack.get("flow_name") or ""
    ok = pack.get("ok")
    steps = pack.get("execution_steps") or []
    traces = pack.get("traces") or []
    lines.append(f"summary: {summary}")
    lines.append(f"flow.name: {flow_name}")
    lines.append(f"ok: {ok}")
    lines.append(f"steps.total: {len(steps)}")
    lines.append(f"steps.skipped: {_count_skips(steps)}")
    lines.append(f"steps.errors: {_count_errors(steps)}")
    lines.append(f"traces.count: {len(traces)}")
    error = pack.get("error")
    if isinstance(error, dict):
        if error.get("kind"):
            lines.append(f"error.kind: {error.get('kind')}")
        if error.get("message"):
            lines.append(f"error.message: {error.get('message')}")
    return "\n".join(lines)


def write_last_execution(root: Path, pack: dict, plain_text: str) -> None:
    execution_dir = root / ".namel3ss" / "execution"
    execution_dir.mkdir(parents=True, exist_ok=True)
    last_json = execution_dir / "last.json"
    last_plain = execution_dir / "last.plain"
    last_json.write_text(_stable_json(pack), encoding="utf-8")
    last_plain.write_text(plain_text.rstrip() + "\n", encoding="utf-8")


def _stable_json(payload: object) -> str:
    import json

    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _count_skips(steps: list[dict]) -> int:
    return sum(1 for step in steps if step.get("kind") in SKIP_KINDS)


def _count_errors(steps: list[dict]) -> int:
    return sum(1 for step in steps if step.get("kind") == "error")


def _normalize_dict(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    return {key: _normalize_value(value[key]) for key in sorted(value.keys())}


def _normalize_list(value: object) -> list:
    if not isinstance(value, list):
        return []
    return [_normalize_value(entry) for entry in value]


def _normalize_value(value: object) -> object:
    if isinstance(value, dict):
        return _normalize_dict(value)
    if isinstance(value, list):
        return _normalize_list(value)
    return value


def _format_literal(value: object) -> str:
    if isinstance(value, str):
        return f"\"{stable_truncate(value, limit=60)}\""
    return summarize_value(value)


def _comparison_op(kind: str) -> str:
    return {
        "gt": ">",
        "lt": "<",
        "gte": ">=",
        "lte": "<=",
        "eq": "==",
        "ne": "!=",
    }.get(kind, "==")


__all__ = [
    "SKIP_KINDS",
    "build_plain_text",
    "format_assignable",
    "format_expression",
    "normalize_graph",
    "stable_bullets",
    "stable_join",
    "stable_truncate",
    "summarize_value",
    "write_last_execution",
]
