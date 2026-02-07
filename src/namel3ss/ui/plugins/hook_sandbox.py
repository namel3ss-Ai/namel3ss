from __future__ import annotations

import ast
from pathlib import Path
from typing import Callable

from namel3ss.errors.base import Namel3ssError
from namel3ss.utils.numbers import is_number, to_decimal

HOOK_ENTRYPOINTS: dict[str, str] = {
    "compiler": "on_compile",
    "runtime": "on_tool_call",
    "studio": "on_studio_load",
}


def load_sandboxed_hook(module_path: Path, *, hook_type: str) -> Callable[[dict], object]:
    entrypoint = HOOK_ENTRYPOINTS.get(str(hook_type).strip().lower())
    if entrypoint is None:
        raise Namel3ssError(f"Unsupported hook type '{hook_type}'.")
    try:
        source = module_path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise Namel3ssError(f"Hook module not found: {module_path.as_posix()}") from err
    try:
        parsed = ast.parse(source, filename=module_path.as_posix())
    except SyntaxError as err:
        raise Namel3ssError(
            f"Hook module '{module_path.as_posix()}' has invalid syntax: {err.msg}",
            line=err.lineno,
            column=err.offset,
        ) from err
    expression = _extract_hook_expression(parsed, module_path=module_path, entrypoint=entrypoint)
    _validate_expression(expression, module_path=module_path)

    def _run(context: dict) -> object:
        env = {"context": dict(context or {})}
        return _eval_expression(expression, env=env, module_path=module_path)

    return _run


def _extract_hook_expression(module_ast: ast.Module, *, module_path: Path, entrypoint: str) -> ast.AST:
    fn = None
    for node in module_ast.body:
        if isinstance(node, ast.FunctionDef) and node.name == entrypoint:
            fn = node
            break
    if fn is None:
        raise Namel3ssError(
            f"Hook module '{module_path.as_posix()}' must define {entrypoint}(context)."
        )
    if fn.decorator_list:
        raise Namel3ssError(
            f"Hook function {entrypoint}() in '{module_path.as_posix()}' cannot use decorators.",
            line=fn.lineno,
            column=fn.col_offset,
        )
    arg_names = [arg.arg for arg in fn.args.args]
    if arg_names != ["context"]:
        raise Namel3ssError(
            f"Hook function {entrypoint}() in '{module_path.as_posix()}' must accept exactly (context).",
            line=fn.lineno,
            column=fn.col_offset,
        )
    if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs or fn.args.posonlyargs:
        raise Namel3ssError(
            f"Hook function {entrypoint}() in '{module_path.as_posix()}' cannot use variadic arguments.",
            line=fn.lineno,
            column=fn.col_offset,
        )
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        raise Namel3ssError(
            f"Hook function {entrypoint}() in '{module_path.as_posix()}' must contain a single return expression.",
            line=fn.lineno,
            column=fn.col_offset,
        )
    if body[0].value is None:
        raise Namel3ssError(
            f"Hook function {entrypoint}() in '{module_path.as_posix()}' cannot return without a value.",
            line=body[0].lineno,
            column=body[0].col_offset,
        )
    return body[0].value


def _validate_expression(node: ast.AST, *, module_path: Path) -> None:
    allowed_types = (
        ast.Constant,
        ast.Name,
        ast.List,
        ast.Tuple,
        ast.Dict,
        ast.Subscript,
        ast.BinOp,
        ast.BoolOp,
        ast.UnaryOp,
        ast.Compare,
        ast.IfExp,
        ast.Load,
        ast.Add,
        ast.And,
        ast.Or,
        ast.Not,
        ast.UAdd,
        ast.USub,
        ast.Eq,
        ast.NotEq,
        ast.Gt,
        ast.Lt,
        ast.GtE,
        ast.LtE,
        ast.In,
        ast.NotIn,
    )
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            raise Namel3ssError(
                f"Hook module '{module_path.as_posix()}' cannot call functions.",
                line=getattr(child, "lineno", None),
                column=getattr(child, "col_offset", None),
            )
        if isinstance(child, ast.Attribute):
            raise Namel3ssError(
                f"Hook module '{module_path.as_posix()}' cannot use attribute access.",
                line=getattr(child, "lineno", None),
                column=getattr(child, "col_offset", None),
            )
        if isinstance(child, ast.Name) and child.id not in {"context", "True", "False", "None"}:
            raise Namel3ssError(
                f"Hook module '{module_path.as_posix()}' may only reference context.",
                line=getattr(child, "lineno", None),
                column=getattr(child, "col_offset", None),
            )
        if not isinstance(child, allowed_types):
            raise Namel3ssError(
                f"Hook module '{module_path.as_posix()}' uses unsupported syntax.",
                line=getattr(child, "lineno", None),
                column=getattr(child, "col_offset", None),
            )


def _eval_expression(node: ast.AST, *, env: dict[str, object], module_path: Path) -> object:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise Namel3ssError(
                f"Unknown symbol '{node.id}' in hook module '{module_path.as_posix()}'.",
                line=node.lineno,
                column=node.col_offset,
            )
        return env[node.id]
    if isinstance(node, ast.List):
        return [_eval_expression(item, env=env, module_path=module_path) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return [_eval_expression(item, env=env, module_path=module_path) for item in node.elts]
    if isinstance(node, ast.Dict):
        result: dict[object, object] = {}
        for key_node, value_node in zip(node.keys, node.values):
            key = _eval_expression(key_node, env=env, module_path=module_path) if key_node is not None else None
            value = _eval_expression(value_node, env=env, module_path=module_path)
            result[key] = value
        return result
    if isinstance(node, ast.Subscript):
        target = _eval_expression(node.value, env=env, module_path=module_path)
        if isinstance(node.slice, ast.Slice):
            raise Namel3ssError(
                f"Hook module '{module_path.as_posix()}' does not support slicing.",
                line=node.lineno,
                column=node.col_offset,
            )
        key = _eval_expression(node.slice, env=env, module_path=module_path)
        try:
            return target[key]  # type: ignore[index]
        except Exception as err:
            raise Namel3ssError(
                f"Hook module '{module_path.as_posix()}' failed to access key '{key}'.",
                line=node.lineno,
                column=node.col_offset,
            ) from err
    if isinstance(node, ast.BinOp):
        left = _eval_expression(node.left, env=env, module_path=module_path)
        right = _eval_expression(node.right, env=env, module_path=module_path)
        if isinstance(node.op, ast.Add):
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if is_number(left) and is_number(right):
                return to_decimal(left) + to_decimal(right)
        raise Namel3ssError(
            f"Hook module '{module_path.as_posix()}' only supports '+' for text or numbers.",
            line=node.lineno,
            column=node.col_offset,
        )
    if isinstance(node, ast.BoolOp):
        values = [_eval_expression(item, env=env, module_path=module_path) for item in node.values]
        if isinstance(node.op, ast.And):
            return all(bool(item) for item in values)
        if isinstance(node.op, ast.Or):
            return any(bool(item) for item in values)
    if isinstance(node, ast.UnaryOp):
        operand = _eval_expression(node.operand, env=env, module_path=module_path)
        if isinstance(node.op, ast.Not):
            return not bool(operand)
        if isinstance(node.op, ast.UAdd):
            if not is_number(operand):
                raise Namel3ssError(
                    f"Hook module '{module_path.as_posix()}' unary '+' requires a number.",
                    line=node.lineno,
                    column=node.col_offset,
                )
            return to_decimal(operand)
        if isinstance(node.op, ast.USub):
            if not is_number(operand):
                raise Namel3ssError(
                    f"Hook module '{module_path.as_posix()}' unary '-' requires a number.",
                    line=node.lineno,
                    column=node.col_offset,
                )
            return -to_decimal(operand)
    if isinstance(node, ast.Compare):
        left = _eval_expression(node.left, env=env, module_path=module_path)
        current = left
        result = True
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_expression(comparator, env=env, module_path=module_path)
            if isinstance(op, ast.Eq):
                ok = current == right
            elif isinstance(op, ast.NotEq):
                ok = current != right
            elif isinstance(op, ast.Gt):
                ok = current > right
            elif isinstance(op, ast.Lt):
                ok = current < right
            elif isinstance(op, ast.GtE):
                ok = current >= right
            elif isinstance(op, ast.LtE):
                ok = current <= right
            elif isinstance(op, ast.In):
                ok = current in right  # type: ignore[operator]
            elif isinstance(op, ast.NotIn):
                ok = current not in right  # type: ignore[operator]
            else:
                raise Namel3ssError(
                    f"Hook module '{module_path.as_posix()}' uses an unsupported comparison.",
                    line=node.lineno,
                    column=node.col_offset,
                )
            result = result and bool(ok)
            if not result:
                return False
            current = right
        return result
    if isinstance(node, ast.IfExp):
        test = _eval_expression(node.test, env=env, module_path=module_path)
        branch = node.body if bool(test) else node.orelse
        return _eval_expression(branch, env=env, module_path=module_path)
    raise Namel3ssError(
        f"Hook module '{module_path.as_posix()}' uses unsupported syntax.",
        line=getattr(node, "lineno", None),
        column=getattr(node, "col_offset", None),
    )


__all__ = ["HOOK_ENTRYPOINTS", "load_sandboxed_hook"]
