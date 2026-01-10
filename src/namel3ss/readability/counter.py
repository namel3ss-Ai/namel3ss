from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar.phase2 import ClearStmt, NoticeStmt, SaveRecordStmt
from namel3ss.parser.sugar.phase3 import ParallelVerbAgentsStmt, VerbAgentCallStmt
from namel3ss.parser.sugar.phase4 import AttemptOtherwiseStmt


class FlowCounter:
    def __init__(self) -> None:
        self.statement_total = 0
        self.max_depth = 0
        self.let_count = 0
        self.find = 0
        self.delete = 0
        self.create = 0
        self.update = 0
        self.save = 0
        self.set_state = 0
        self.try_catch = 0
        self.list_get = 0
        self.list_length = 0
        self.list_op_total = 0
        self.map_get = 0
        self.map_op_total = 0
        self.index_patterns = 0
        self.ask_ai = 0
        self.run_agent = 0
        self.run_parallel = 0
        self.comparisons = 0
        self.branches = 0
        self.record_refs: set[str] = set()
        self.state_paths: set[str] = set()

    def walk_statement(self, stmt: ast.Statement, *, depth: int) -> None:
        self.statement_total += 1
        self.max_depth = max(self.max_depth, depth)

        if isinstance(stmt, ast.Let):
            self.let_count += 1
            if "index" in stmt.name.lower():
                self.index_patterns += 1
            self._walk_expression(stmt.expression)
            return
        if isinstance(stmt, SaveRecordStmt):
            self.save += 1
            self.record_refs.add(stmt.record_name)
            for field in stmt.fields:
                self._walk_expression(field.expression)
            return
        if isinstance(stmt, ast.Set):
            if isinstance(stmt.target, ast.StatePath):
                self.set_state += 1
                self.state_paths.add(".".join(stmt.target.path))
            self._walk_expression(stmt.expression)
            return
        if isinstance(stmt, ast.Find):
            self.find += 1
            self.record_refs.add(stmt.record_name)
            self._walk_expression(stmt.predicate)
            return
        if isinstance(stmt, ast.Delete):
            self.delete += 1
            self.record_refs.add(stmt.record_name)
            self._walk_expression(stmt.predicate)
            return
        if isinstance(stmt, ast.Create):
            self.create += 1
            self.record_refs.add(stmt.record_name)
            self._walk_expression(stmt.values)
            return
        if isinstance(stmt, ast.Update):
            self.update += 1
            self.record_refs.add(stmt.record_name)
            self._walk_expression(stmt.predicate)
            for update in stmt.updates:
                self._walk_expression(update.expression)
            return
        if isinstance(stmt, ast.Save):
            self.save += 1
            self.record_refs.add(stmt.record_name)
            return
        if isinstance(stmt, ClearStmt):
            self.delete += 1
            for record_name in stmt.record_names:
                self.record_refs.add(record_name)
            return
        if isinstance(stmt, NoticeStmt):
            return
        if isinstance(stmt, VerbAgentCallStmt):
            self.run_agent += 1
            self._walk_expression(stmt.input_expr)
            return
        if isinstance(stmt, ParallelVerbAgentsStmt):
            self.run_parallel += 1
            for entry in stmt.entries:
                self._walk_expression(entry.input_expr)
            return
        if isinstance(stmt, AttemptOtherwiseStmt):
            self.try_catch += 1
            for item in stmt.try_body:
                self.walk_statement(item, depth=depth + 1)
            for item in stmt.catch_body:
                self.walk_statement(item, depth=depth + 1)
            return
        if isinstance(stmt, ast.TryCatch):
            self.try_catch += 1
            for item in stmt.try_body:
                self.walk_statement(item, depth=depth + 1)
            for item in stmt.catch_body:
                self.walk_statement(item, depth=depth + 1)
            return
        if isinstance(stmt, ast.If):
            self.branches += 1
            self._walk_expression(stmt.condition)
            for item in stmt.then_body:
                self.walk_statement(item, depth=depth + 1)
            for item in stmt.else_body:
                self.walk_statement(item, depth=depth + 1)
            return
        if isinstance(stmt, ast.Match):
            self.branches += 1
            self._walk_expression(stmt.expression)
            for case in stmt.cases:
                self._walk_expression(case.pattern)
                for item in case.body:
                    self.walk_statement(item, depth=depth + 1)
            if stmt.otherwise:
                for item in stmt.otherwise:
                    self.walk_statement(item, depth=depth + 1)
            return
        if isinstance(stmt, ast.Repeat):
            self.branches += 1
            self._walk_expression(stmt.count)
            for item in stmt.body:
                self.walk_statement(item, depth=depth + 1)
            return
        if isinstance(stmt, ast.RepeatWhile):
            self.branches += 1
            self._walk_expression(stmt.condition)
            for item in stmt.body:
                self.walk_statement(item, depth=depth + 1)
            return
        if isinstance(stmt, ast.ForEach):
            self.branches += 1
            self._walk_expression(stmt.iterable)
            for item in stmt.body:
                self.walk_statement(item, depth=depth + 1)
            return
        if isinstance(stmt, ast.AskAIStmt):
            self.ask_ai += 1
            self._walk_expression(stmt.input_expr)
            return
        if isinstance(stmt, ast.RunAgentStmt):
            self.run_agent += 1
            self._walk_expression(stmt.input_expr)
            return
        if isinstance(stmt, ast.RunAgentsParallelStmt):
            self.run_parallel += 1
            for entry in stmt.entries:
                self._walk_expression(entry.input_expr)
            return
        if isinstance(stmt, ast.ParallelBlock):
            for task in stmt.tasks:
                for item in task.body:
                    self.walk_statement(item, depth=depth + 1)
            return
        if isinstance(stmt, ast.Return):
            self._walk_expression(stmt.expression)
            return

    def _walk_expression(self, expr: ast.Expression | None) -> None:
        if expr is None:
            return
        if isinstance(expr, ast.Comparison):
            self.comparisons += 1
            self._walk_expression(expr.left)
            self._walk_expression(expr.right)
            return
        if isinstance(expr, ast.UnaryOp):
            self._walk_expression(expr.operand)
            return
        if isinstance(expr, ast.BinaryOp):
            if _is_count_minus_one(expr):
                self.index_patterns += 1
            self._walk_expression(expr.left)
            self._walk_expression(expr.right)
            return
        if isinstance(expr, ast.ToolCallExpr):
            for arg in expr.arguments:
                self._walk_expression(arg.value)
            return
        if isinstance(expr, ast.CallFunctionExpr):
            for arg in expr.arguments:
                self._walk_expression(arg.value)
            return
        if isinstance(expr, ast.ListExpr):
            for item in expr.items:
                self._walk_expression(item)
            return
        if isinstance(expr, ast.MapExpr):
            for entry in expr.entries:
                self._walk_expression(entry.key)
                self._walk_expression(entry.value)
            return
        if isinstance(expr, ast.ListOpExpr):
            self.list_op_total += 1
            if expr.kind == "get":
                self.list_get += 1
            if expr.kind == "length":
                self.list_length += 1
            self._walk_expression(expr.target)
            self._walk_expression(expr.value)
            self._walk_expression(expr.index)
            return
        if isinstance(expr, ast.MapOpExpr):
            self.map_op_total += 1
            if expr.kind == "get":
                self.map_get += 1
            self._walk_expression(expr.target)
            self._walk_expression(expr.key)
            self._walk_expression(expr.value)
            return
        if isinstance(expr, ast.ListMapExpr):
            self.list_op_total += 1
            self._walk_expression(expr.target)
            self._walk_expression(expr.body)
            return
        if isinstance(expr, ast.ListFilterExpr):
            self.list_op_total += 1
            self._walk_expression(expr.target)
            self._walk_expression(expr.predicate)
            return
        if isinstance(expr, ast.ListReduceExpr):
            self.list_op_total += 1
            self._walk_expression(expr.target)
            self._walk_expression(expr.start)
            self._walk_expression(expr.body)


def _is_count_minus_one(expr: ast.BinaryOp) -> bool:
    if expr.op != "-":
        return False
    if not isinstance(expr.right, ast.Literal) or expr.right.value != 1:
        return False
    if isinstance(expr.left, ast.VarReference) and "count" in expr.left.name.lower():
        return True
    return False


__all__ = ["FlowCounter"]
