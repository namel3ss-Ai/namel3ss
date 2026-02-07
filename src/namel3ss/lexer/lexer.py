from __future__ import annotations

from decimal import Decimal
from typing import List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lexer.tokens import ESCAPED_IDENTIFIER, KEYWORDS, Token


_PUNCTUATION_TOKENS = {
    ":": "COLON",
    ".": "DOT",
    "+": "PLUS",
    "-": "MINUS",
    "/": "SLASH",
    "%": "PERCENT",
    "=": "EQUALS",
    "(": "LPAREN",
    ")": "RPAREN",
    "[": "LBRACKET",
    "]": "RBRACKET",
    "{": "LBRACE",
    "}": "RBRACE",
    ",": "COMMA",
    "<": "LT",
    ">": "GT",
    "|": "PIPE",
    "!": "BANG",
}

_ESCAPE_TABLE = {
    "n": "\n",
    "t": "\t",
    '"': '"',
    "\\": "\\",
}


class Lexer:
    """Line-aware lexer with indentation and string escape support."""

    def __init__(self, source: str) -> None:
        self.source = source

    def tokenize(self) -> List[Token]:
        # Keep native scanner for plain inputs, but force python fallback when
        # new lexer features are present so behavior stays deterministic.
        use_fallback = any(token in self.source for token in ('"""', "\\", "#", "|", "==", "!=", "<=", ">=", "{", "}"))
        if not use_fallback:
            from namel3ss.lexer.native_scan import scan_tokens_native

            native_tokens = scan_tokens_native(self.source)
            if native_tokens is not None:
                return native_tokens
        return self._tokenize_python()

    def _tokenize_python(self) -> List[Token]:
        tokens: List[Token] = []
        indent_stack = [0]
        lines = self.source.splitlines()
        idx = 0

        while idx < len(lines):
            raw_line = lines[idx]
            if raw_line.strip() == "" or raw_line.lstrip().startswith("#"):
                idx += 1
                continue

            indent = self._leading_spaces(raw_line)
            line_no = idx + 1
            if indent > indent_stack[-1]:
                tokens.append(Token("INDENT", None, line_no, 1))
                indent_stack.append(indent)
            else:
                while indent < indent_stack[-1]:
                    indent_stack.pop()
                    tokens.append(Token("DEDENT", None, line_no, 1))
                if indent != indent_stack[-1]:
                    raise Namel3ssError(
                        f"Inconsistent indentation (got {indent} spaces, expected {indent_stack[-1]})",
                        line=line_no,
                        column=1,
                    )

            line_tokens, end_line_idx = self._scan_line(lines, idx, indent)
            tokens.extend(line_tokens)
            end_line = lines[end_line_idx]
            tokens.append(Token("NEWLINE", None, end_line_idx + 1, len(end_line) + 1))
            idx = end_line_idx + 1

        while len(indent_stack) > 1:
            indent_stack.pop()
            tokens.append(Token("DEDENT", None, len(lines), 1))

        tokens.append(Token("EOF", None, len(lines) + 1, 1))
        return tokens

    @staticmethod
    def _leading_spaces(text: str) -> int:
        count = 0
        for ch in text:
            if ch == " ":
                count += 1
            else:
                break
        return count

    def _scan_line(self, lines: list[str], start_idx: int, indent: int) -> tuple[List[Token], int]:
        tokens: List[Token] = []
        line_idx = start_idx
        line = lines[line_idx]
        i = indent
        while True:
            if i >= len(line):
                return tokens, line_idx
            ch = line[i]
            column = i + 1
            if ch == " ":
                i += 1
                continue
            if ch == "#":
                return tokens, line_idx
            if ch == "*":
                if i + 1 < len(line) and line[i + 1] == "*":
                    tokens.append(Token("POWER", "**", line_idx + 1, column))
                    i += 2
                    continue
                tokens.append(Token("STAR", "*", line_idx + 1, column))
                i += 1
                continue
            token_type = _PUNCTUATION_TOKENS.get(ch)
            if token_type is not None:
                tokens.append(Token(token_type, ch, line_idx + 1, column))
                i += 1
                continue
            if ch == "`":
                value, consumed = self._read_escaped_identifier(line[i:], line_idx + 1, column)
                tokens.append(Token(ESCAPED_IDENTIFIER, value, line_idx + 1, column, escaped=True))
                i += consumed
                continue
            if ch == '"':
                value, end_line_idx, end_offset = self._read_string(lines, line_idx, i)
                tokens.append(Token("STRING", value, line_idx + 1, column))
                line_idx = end_line_idx
                line = lines[line_idx]
                i = end_offset
                continue
            if ch.isdigit():
                value, consumed = self._read_number(line[i:])
                tokens.append(Token("NUMBER", value, line_idx + 1, column))
                i += consumed
                continue
            if ch.isalpha() or ch == "_":
                value, consumed = self._read_identifier(line[i:])
                token_type = KEYWORDS.get(value, "IDENT")
                token_value = self._keyword_value(token_type, value)
                tokens.append(Token(token_type, token_value, line_idx + 1, column))
                i += consumed
                continue
            raise Namel3ssError(_unsupported_character_message(ch), line=line_idx + 1, column=column)

    def _read_string(self, lines: list[str], line_idx: int, start_col_idx: int) -> tuple[str, int, int]:
        line = lines[line_idx]
        if line.startswith('"""', start_col_idx):
            return self._read_triple_string(lines, line_idx, start_col_idx)
        return self._read_single_string(line, line_idx, start_col_idx)

    def _read_single_string(self, line: str, line_idx: int, start_col_idx: int) -> tuple[str, int, int]:
        assert line[start_col_idx] == '"'
        value_chars: list[str] = []
        i = start_col_idx + 1
        while i < len(line):
            ch = line[i]
            if ch == '"':
                return "".join(value_chars), line_idx, i + 1
            if ch == "\\":
                escaped, consumed = self._read_escape(line, line_idx, i, in_multiline=False)
                value_chars.append(escaped)
                i += consumed
                continue
            value_chars.append(ch)
            i += 1
        raise Namel3ssError("Unterminated string literal", line=line_idx + 1, column=start_col_idx + 1)

    def _read_triple_string(self, lines: list[str], line_idx: int, start_col_idx: int) -> tuple[str, int, int]:
        value_chars: list[str] = []
        current_line_idx = line_idx
        i = start_col_idx + 3
        while current_line_idx < len(lines):
            line = lines[current_line_idx]
            while i < len(line):
                if line.startswith('"""', i):
                    return "".join(value_chars), current_line_idx, i + 3
                ch = line[i]
                if ch == "\\":
                    escaped, consumed = self._read_escape(line, current_line_idx, i, in_multiline=True)
                    value_chars.append(escaped)
                    i += consumed
                    continue
                value_chars.append(ch)
                i += 1
            current_line_idx += 1
            if current_line_idx >= len(lines):
                break
            value_chars.append("\n")
            i = 0
        raise Namel3ssError(
            "Unterminated triple-quoted string literal",
            line=line_idx + 1,
            column=start_col_idx + 1,
        )

    def _read_escape(self, line: str, line_idx: int, index: int, *, in_multiline: bool) -> tuple[str, int]:
        if index + 1 >= len(line):
            if in_multiline:
                return "\\", 1
            raise Namel3ssError(_unsupported_escape_message(""), line=line_idx + 1, column=index + 1)
        marker = line[index + 1]
        mapped = _ESCAPE_TABLE.get(marker)
        if mapped is None:
            raise Namel3ssError(_unsupported_escape_message(marker), line=line_idx + 1, column=index + 1)
        return mapped, 2

    @staticmethod
    def _read_number(text: str) -> tuple[Decimal, int]:
        i = 0
        digits: list[str] = []
        while i < len(text) and text[i].isdigit():
            digits.append(text[i])
            i += 1
        if i < len(text) and text[i] == "." and i + 1 < len(text) and text[i + 1].isdigit():
            digits.append(".")
            i += 1
            while i < len(text) and text[i].isdigit():
                digits.append(text[i])
                i += 1
        return Decimal("".join(digits)), i

    @staticmethod
    def _read_identifier(text: str) -> tuple[str, int]:
        i = 0
        chars: list[str] = []
        while i < len(text) and (text[i].isalnum() or text[i] == "_"):
            chars.append(text[i])
            i += 1
        return "".join(chars), i

    @staticmethod
    def _read_escaped_identifier(text: str, line: int, column: int) -> tuple[str, int]:
        assert text[0] == "`"
        end = text.find("`", 1)
        if end == -1:
            raise Namel3ssError("Unterminated escaped identifier", line=line, column=column)
        value = text[1:end]
        if value == "":
            raise Namel3ssError("Escaped identifier cannot be empty", line=line, column=column)
        if not _is_identifier_text(value):
            raise Namel3ssError(
                build_guidance_message(
                    what="Escaped identifier contains invalid characters.",
                    why="Escaped identifiers use the same characters as normal identifiers.",
                    fix="Use letters, numbers, or underscores inside the backticks.",
                    example='let `title` is "..."',
                ),
                line=line,
                column=column,
            )
        return value, end + 1

    @staticmethod
    def _keyword_value(token_type: str, raw: str):
        if token_type == "BOOLEAN":
            return raw.lower() == "true"
        return raw


def _is_identifier_text(value: str) -> bool:
    if not value:
        return False
    first = value[0]
    if not (first.isalpha() or first == "_"):
        return False
    for ch in value[1:]:
        if not (ch.isalnum() or ch == "_"):
            return False
    return True


def _unsupported_character_message(ch: str) -> str:
    return build_guidance_message(
        what=f"Unsupported character '{ch}' in namel3ss source.",
        why="Only supported operators are +, -, *, / and comparison words like `is greater than`.",
        fix="Remove the character or rewrite using supported arithmetic/comparison syntax.",
        example="Use `total + 2.5` or `if price is greater than 10:`.",
    )


def _unsupported_escape_message(marker: str) -> str:
    value = f"\\{marker}" if marker else "\\"
    return build_guidance_message(
        what=f"Unsupported escape sequence '{value}'.",
        why="Only \\n, \\t, \\\\, and \\\" are supported.",
        fix="Use a supported escape sequence.",
        example='text is "line one\\nline two"',
    )

