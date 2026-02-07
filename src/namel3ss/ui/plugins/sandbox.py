from __future__ import annotations

import ast
from pathlib import Path
from typing import Callable

from namel3ss.errors.base import Namel3ssError
from namel3ss.utils.numbers import is_number, to_decimal


def load_sandboxed_renderer(module_path: Path) -> Callable[[dict, dict], list[dict]]:
    try:
        source = module_path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise Namel3ssError(f"UI plugin module not found: {module_path.as_posix()}") from err

    try:
        parsed = ast.parse(source, filename=module_path.as_posix())
    except SyntaxError as err:
        raise Namel3ssError(
            f"UI plugin module '{module_path.as_posix()}' has invalid syntax: {err.msg}",
            line=err.lineno,
            column=err.offset,
        ) from err

    render_func = _extract_render_function(parsed, module_path)
    expression = _extract_render_expression(render_func, module_path)
    _validate_expression(expression, module_path)

    def _render(props: dict, state: dict) -> list[dict]:
        env = {"props": props, "state": state}
        value = _eval_expression(expression, env, module_path)
        if not isinstance(value, list):
            raise Namel3ssError(f"UI plugin renderer '{module_path.as_posix()}' must return a list of nodes.")
        nodes: list[dict] = []
        for idx, node in enumerate(value):
            if not isinstance(node, dict):
                raise Namel3ssError(
                    f"UI plugin renderer '{module_path.as_posix()}' returned node[{idx}] that is not a mapping."
                )
            nodes.append(node)
        return nodes

    return _render


def _extract_render_function(module_ast: ast.Module, module_path: Path) -> ast.FunctionDef:
    functions = [node for node in module_ast.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1 or functions[0].name != "render":
        raise Namel3ssError(
            f"UI plugin module '{module_path.as_posix()}' must define exactly one function: render(props, state)."
        )
    fn = functions[0]
    if fn.decorator_list:
        raise Namel3ssError(
            f"UI plugin module '{module_path.as_posix()}' cannot decorate render().",
            line=fn.lineno,
            column=fn.col_offset,
        )
    arg_names = [arg.arg for arg in fn.args.args]
    if arg_names != ["props", "state"]:
        raise Namel3ssError(
            f"UI plugin render() in '{module_path.as_posix()}' must accept exactly (props, state).",
            line=fn.lineno,
            column=fn.col_offset,
        )
    if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs or fn.args.posonlyargs:
        raise Namel3ssError(
            f"UI plugin render() in '{module_path.as_posix()}' cannot use variadic or keyword-only arguments.",
            line=fn.lineno,
            column=fn.col_offset,
        )
    return fn


def _extract_render_expression(fn: ast.FunctionDef, module_path: Path) -> ast.AST:
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        raise Namel3ssError(
            f"UI plugin render() in '{module_path.as_posix()}' must contain a single return expression.",
            line=fn.lineno,
            column=fn.col_offset,
        )
    if body[0].value is None:
        raise Namel3ssError(
            f"UI plugin render() in '{module_path.as_posix()}' cannot return without a value.",
            line=body[0].lineno,
            column=body[0].col_offset,
        )
    return body[0].value


def _validate_expression(node: ast.AST, module_path: Path) -> None:
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
                f"UI plugin module '{module_path.as_posix()}' cannot call functions inside render().",
                line=getattr(child, "lineno", None),
                column=getattr(child, "col_offset", None),
            )
        if isinstance(child, ast.Attribute):
            raise Namel3ssError(
                f"UI plugin module '{module_path.as_posix()}' cannot use attribute access inside render().",
                line=getattr(child, "lineno", None),
                column=getattr(child, "col_offset", None),
            )
        if isinstance(child, ast.Name) and child.id not in {"props", "state", "True", "False", "None"}:
            raise Namel3ssError(
                f"UI plugin module '{module_path.as_posix()}' may only reference props and state.",
                line=getattr(child, "lineno", None),
                column=getattr(child, "col_offset", None),
            )
        if not isinstance(child, allowed_types):
            raise Namel3ssError(
                f"UI plugin module '{module_path.as_posix()}' uses unsupported syntax in render().",
                line=getattr(child, "lineno", None),
                column=getattr(child, "col_offset", None),
            )


def _eval_expression(node: ast.AST, env: dict[str, object], module_path: Path) -> object:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise Namel3ssError(
                f"Unknown symbol '{node.id}' in UI plugin renderer '{module_path.as_posix()}'.",
                line=node.lineno,
                column=node.col_offset,
            )
        return env[node.id]
    if isinstance(node, ast.List):
        return [_eval_expression(child, env, module_path) for child in node.elts]
    if isinstance(node, ast.Tuple):
        return [_eval_expression(child, env, module_path) for child in node.elts]
    if isinstance(node, ast.Dict):
        result: dict[object, object] = {}
        for key_node, value_node in zip(node.keys, node.values):
            key = _eval_expression(key_node, env, module_path) if key_node is not None else None
            if not isinstance(key, str):
                raise Namel3ssError(
                    f"UI plugin renderer '{module_path.as_posix()}' requires dictionary keys to be text.",
                    line=getattr(key_node, "lineno", None),
                    column=getattr(key_node, "col_offset", None),
                )
            value = _eval_expression(value_node, env, module_path)
            result[key] = value
        return result
    if isinstance(node, ast.Subscript):
        target = _eval_expression(node.value, env, module_path)
        key_node = node.slice
        if isinstance(key_node, ast.Slice):
            raise Namel3ssError(
                f"UI plugin renderer '{module_path.as_posix()}' does not support slicing.",
                line=node.lineno,
                column=node.col_offset,
            )
        key = _eval_expression(key_node, env, module_path)
        try:
            return target[key]  # type: ignore[index]
        except Exception as err:
            raise Namel3ssError(
                f"UI plugin renderer '{module_path.as_posix()}' failed to access key '{key}'.",
                line=node.lineno,
                column=node.col_offset,
            ) from err
    if isinstance(node, ast.BinOp):
        left = _eval_expression(node.left, env, module_path)
        right = _eval_expression(node.right, env, module_path)
        if isinstance(node.op, ast.Add):
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if is_number(left) and is_number(right):
                return to_decimal(left) + to_decimal(right)
        raise Namel3ssError(
            f"UI plugin renderer '{module_path.as_posix()}' only supports '+' for strings or numbers.",
            line=node.lineno,
            column=node.col_offset,
        )
    if isinstance(node, ast.BoolOp):
        values = [_eval_expression(value, env, module_path) for value in node.values]
        if isinstance(node.op, ast.And):
            result = True
            for value in values:
                if not isinstance(value, bool):
                    raise Namel3ssError(
                        f"UI plugin renderer '{module_path.as_posix()}' requires boolean values for 'and'.",
                        line=node.lineno,
                        column=node.col_offset,
                    )
                result = result and value
                if not result:
                    break
            return result
        if isinstance(node.op, ast.Or):
            result = False
            for value in values:
                if not isinstance(value, bool):
                    raise Namel3ssError(
                        f"UI plugin renderer '{module_path.as_posix()}' requires boolean values for 'or'.",
                        line=node.lineno,
                        column=node.col_offset,
                    )
                result = result or value
                if result:
                    break
            return result
    if isinstance(node, ast.UnaryOp):
        operand = _eval_expression(node.operand, env, module_path)
        if isinstance(node.op, ast.Not):
            if not isinstance(operand, bool):
                raise Namel3ssError(
                    f"UI plugin renderer '{module_path.as_posix()}' requires boolean values for 'not'.",
                    line=node.lineno,
                    column=node.col_offset,
                )
            return not operand
        if isinstance(node.op, ast.UAdd):
            if not is_number(operand):
                raise Namel3ssError(
                    f"UI plugin renderer '{module_path.as_posix()}' unary '+' requires a number.",
                    line=node.lineno,
                    column=node.col_offset,
                )
            return to_decimal(operand)
        if isinstance(node.op, ast.USub):
            if not is_number(operand):
                raise Namel3ssError(
                    f"UI plugin renderer '{module_path.as_posix()}' unary '-' requires a number.",
                    line=node.lineno,
                    column=node.col_offset,
                )
            return -to_decimal(operand)
    if isinstance(node, ast.Compare):
        left = _eval_expression(node.left, env, module_path)
        result = True
        current_left = left
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_expression(comparator, env, module_path)
            if isinstance(op, ast.Eq):
                ok = current_left == right
            elif isinstance(op, ast.NotEq):
                ok = current_left != right
            elif isinstance(op, ast.Gt):
                ok = current_left > right
            elif isinstance(op, ast.Lt):
                ok = current_left < right
            elif isinstance(op, ast.GtE):
                ok = current_left >= right
            elif isinstance(op, ast.LtE):
                ok = current_left <= right
            elif isinstance(op, ast.In):
                ok = current_left in right  # type: ignore[operator]
            elif isinstance(op, ast.NotIn):
                ok = current_left not in right  # type: ignore[operator]
            else:
                raise Namel3ssError(
                    f"UI plugin renderer '{module_path.as_posix()}' uses unsupported comparison operator.",
                    line=node.lineno,
                    column=node.col_offset,
                )
            result = result and bool(ok)
            if not result:
                return False
            current_left = right
        return result
    if isinstance(node, ast.IfExp):
        test = _eval_expression(node.test, env, module_path)
        if not isinstance(test, bool):
            raise Namel3ssError(
                f"UI plugin renderer '{module_path.as_posix()}' conditional test must be boolean.",
                line=node.lineno,
                column=node.col_offset,
            )
        branch = node.body if test else node.orelse
        return _eval_expression(branch, env, module_path)

    raise Namel3ssError(
        f"UI plugin renderer '{module_path.as_posix()}' uses unsupported syntax.",
        line=getattr(node, "lineno", None),
        column=getattr(node, "col_offset", None),
    )


__all__ = ["load_sandboxed_renderer"]
