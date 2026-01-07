from __future__ import annotations

from namel3ss.lexer.lexer import Lexer


def build_calc_assignment_index(source: str) -> dict[int, dict[str, int]]:
    tokens = Lexer(source).tokenize()
    lines = source.splitlines()
    index: dict[int, dict[str, int]] = {}
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
            depth = max(depth - 1, 0)
            prev_type = "DEDENT"
            idx += 1
            continue
        if _is_calc_header(tokens, idx, prev_type):
            depth_before = depth
            idx += 4  # calc IDENT, COLON, NEWLINE, INDENT
            depth += 1
            current: dict[str, int] | None = None
            last_content_line: int | None = None
            prev_type = "INDENT"
            while idx < len(tokens):
                tok = tokens[idx]
                if tok.type == "INDENT":
                    depth += 1
                    prev_type = "INDENT"
                    idx += 1
                    continue
                if tok.type == "DEDENT":
                    depth = max(depth - 1, 0)
                    prev_type = "DEDENT"
                    idx += 1
                    if depth == depth_before:
                        _finalize_assignment(index, current, last_content_line, lines)
                        break
                    continue
                if tok.type == "NEWLINE":
                    prev_type = "NEWLINE"
                    idx += 1
                    continue
                last_content_line = tok.line
                if depth == depth_before + 1 and _is_line_start(prev_type):
                    if current:
                        current["line_end"] = max(tok.line - 1, current["line_start"])
                        _finalize_assignment(index, current, last_content_line, lines)
                    current = {"line_start": tok.line}
                prev_type = tok.type
                idx += 1
            continue
        prev_type = tok.type
        idx += 1
    return index


def _finalize_assignment(
    index: dict[int, dict[str, int]],
    current: dict[str, int] | None,
    last_content_line: int | None,
    lines: list[str],
) -> None:
    if not current:
        return
    line_start = current.get("line_start") or 1
    line_end = current.get("line_end") or last_content_line or line_start
    if line_end < line_start:
        line_end = line_start
    column_end = _column_end(lines, line_end)
    index[line_start] = {"line_end": line_end, "column_end": column_end}


def _column_end(lines: list[str], line_end: int) -> int:
    if 1 <= line_end <= len(lines):
        length = len(lines[line_end - 1])
        return length if length > 0 else 1
    return 1


def _is_calc_header(tokens: list, idx: int, prev_type: str) -> bool:
    tok = tokens[idx]
    if tok.type != "IDENT" or tok.value != "calc":
        return False
    if not _is_line_start(prev_type):
        return False
    if idx + 3 >= len(tokens):
        return False
    return (
        tokens[idx + 1].type == "COLON"
        and tokens[idx + 2].type == "NEWLINE"
        and tokens[idx + 3].type == "INDENT"
    )


def _is_line_start(prev_type: str) -> bool:
    return prev_type in {"NEWLINE", "INDENT", "DEDENT"}


__all__ = ["build_calc_assignment_index"]
