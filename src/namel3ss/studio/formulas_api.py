from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.lexer.lexer import Lexer
from namel3ss.parser.core import parse


def get_formulas_payload(source: str) -> dict:
    try:
        blocks = _extract_calc_blocks(source)
        flow_map = _flow_line_map(source)
        for block in blocks:
            flow_name = _resolve_flow(block, flow_map)
            block["flow"] = flow_name
        return {"ok": True, "schema_version": 1, "blocks": blocks}
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="parse", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")


def _extract_calc_blocks(source: str) -> list[dict]:
    tokens = Lexer(source).tokenize()
    lines = source.splitlines()
    blocks: list[dict] = []
    depth = 0
    idx = 0
    prev_type = "NEWLINE"
    while idx < len(tokens):
        tok = tokens[idx]
        if tok.type == "INDENT":
            depth += 1
            prev_type = "INDENT"
            idx += 1
            continue
        if tok.type == "DEDENT":
            depth -= 1
            prev_type = "DEDENT"
            idx += 1
            continue
        if _is_calc_header(tokens, idx, prev_type):
            header_line = tok.line
            depth_before = depth
            idx += 4  # calc IDENT, COLON, NEWLINE, INDENT
            depth += 1
            block = {"line": header_line, "assignments": []}
            current = None
            last_content_line = None
            prev_type = "INDENT"
            while idx < len(tokens):
                tok = tokens[idx]
                if tok.type == "INDENT":
                    depth += 1
                    prev_type = "INDENT"
                    idx += 1
                    continue
                if tok.type == "DEDENT":
                    depth -= 1
                    prev_type = "DEDENT"
                    idx += 1
                    if depth == depth_before:
                        if current:
                            _finalize_assignment(current, last_content_line)
                            block["assignments"].append(current)
                        blocks.append(_build_block(block, lines))
                        break
                    continue
                if tok.type == "NEWLINE":
                    prev_type = "NEWLINE"
                    idx += 1
                    continue
                last_content_line = tok.line
                if depth == depth_before + 1 and _is_line_start(prev_type):
                    if current:
                        current["line_end"] = tok.line - 1
                        block["assignments"].append(current)
                    current = {"line_start": tok.line}
                prev_type = tok.type
                idx += 1
            continue
        prev_type = tok.type
        idx += 1
    return blocks


def _is_calc_header(tokens: list, idx: int, prev_type: str) -> bool:
    tok = tokens[idx]
    if tok.type != "IDENT" or tok.value != "calc":
        return False
    if not _is_line_start(prev_type):
        return False
    if idx + 3 >= len(tokens):
        return False
    return tokens[idx + 1].type == "COLON" and tokens[idx + 2].type == "NEWLINE" and tokens[idx + 3].type == "INDENT"


def _is_line_start(prev_type: str) -> bool:
    return prev_type in {"NEWLINE", "INDENT", "DEDENT"}


def _finalize_assignment(assignment: dict, last_line: int | None) -> None:
    if "line_end" not in assignment:
        assignment["line_end"] = last_line or assignment["line_start"]
    if assignment["line_end"] < assignment["line_start"]:
        assignment["line_end"] = assignment["line_start"]


def _build_block(block: dict, lines: list[str]) -> dict:
    assignments: list[dict] = []
    for idx, entry in enumerate(block.get("assignments") or []):
        line_start = entry.get("line_start") or 1
        line_end = entry.get("line_end") or line_start
        assignment = _build_assignment(lines, line_start, line_end)
        assignment["id"] = f"calc-{block.get('line', 0)}-{idx}"
        assignments.append(assignment)
    return {"id": f"calc-{block.get('line', 0)}", "line": block.get("line"), "assignments": assignments}


def _build_assignment(lines: list[str], line_start: int, line_end: int) -> dict:
    if line_start < 1:
        line_start = 1
    if line_end < line_start:
        line_end = line_start
    segment = lines[line_start - 1 : line_end] if line_start <= len(lines) else []
    header = segment[0] if segment else ""
    lhs, rhs = _split_assignment(header)
    body = _trim_indent(segment[1:])
    return {
        "line_start": line_start,
        "line_end": line_end,
        "lhs": lhs,
        "rhs": rhs,
        "body": body,
        "code": "\n".join(segment),
    }


def _split_assignment(line: str) -> tuple[str, str]:
    if "=" not in line:
        return line.strip(), ""
    lhs, rhs = line.split("=", 1)
    return lhs.strip(), rhs.strip()


def _trim_indent(lines: list[str]) -> list[str]:
    if not lines:
        return []
    indents = [len(line) - len(line.lstrip(" ")) for line in lines if line.strip()]
    if not indents:
        return ["" for _ in lines]
    trim = min(indents)
    return [line[trim:] if len(line) >= trim else line.lstrip(" ") for line in lines]


def _flow_line_map(source: str) -> dict[int, str]:
    try:
        program = parse(source)
    except Namel3ssError:
        return {}
    line_map: dict[int, str] = {}
    for flow in program.flows:
        _collect_statement_lines(flow.body, flow.name, line_map)
    return line_map


def _collect_statement_lines(statements: list[ast.Statement], flow_name: str, line_map: dict[int, str]) -> None:
    for stmt in statements:
        if stmt.line:
            line_map.setdefault(stmt.line, flow_name)
        if isinstance(stmt, ast.If):
            _collect_statement_lines(stmt.then_body, flow_name, line_map)
            _collect_statement_lines(stmt.else_body, flow_name, line_map)
        elif isinstance(stmt, ast.Repeat):
            _collect_statement_lines(stmt.body, flow_name, line_map)
        elif isinstance(stmt, ast.RepeatWhile):
            _collect_statement_lines(stmt.body, flow_name, line_map)
        elif isinstance(stmt, ast.ForEach):
            _collect_statement_lines(stmt.body, flow_name, line_map)
        elif isinstance(stmt, ast.Match):
            for case in stmt.cases:
                _collect_statement_lines(case.body, flow_name, line_map)
            if stmt.otherwise:
                _collect_statement_lines(stmt.otherwise, flow_name, line_map)
        elif isinstance(stmt, ast.ParallelBlock):
            for task in stmt.tasks:
                _collect_statement_lines(task.body, flow_name, line_map)
        elif isinstance(stmt, ast.TryCatch):
            _collect_statement_lines(stmt.try_body, flow_name, line_map)
            _collect_statement_lines(stmt.catch_body, flow_name, line_map)


def _resolve_flow(block: dict, flow_map: dict[int, str]) -> str | None:
    for assignment in block.get("assignments") or []:
        line = assignment.get("line_start")
        if isinstance(line, int) and line in flow_map:
            return flow_map[line]
    return None


__all__ = ["get_formulas_payload"]
