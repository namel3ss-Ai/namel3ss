from __future__ import annotations

from typing import List

from namel3ss.errors.base import Namel3ssError
from namel3ss.lexer.tokens import KEYWORDS, Token


class Lexer:
    """Line-based lexer with indentation awareness."""

    def __init__(self, source: str) -> None:
        self.source = source

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        indent_stack = [0]
        lines = self.source.splitlines()

        for line_no, raw_line in enumerate(lines, start=1):
            stripped = raw_line.rstrip("\n")
            if stripped.strip() == "":
                continue

            indent = self._leading_spaces(stripped)
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

            line_tokens = self._scan_line(stripped.lstrip(" "), line_no, indent + 1)
            tokens.extend(line_tokens)
            tokens.append(Token("NEWLINE", None, line_no, len(stripped) + 1))

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

    def _scan_line(self, text: str, line_no: int, start_col: int) -> List[Token]:
        tokens: List[Token] = []
        i = 0
        column = start_col
        while i < len(text):
            ch = text[i]
            if ch == " ":
                i += 1
                column += 1
                continue
            if ch == ":":
                tokens.append(Token("COLON", ":", line_no, column))
                i += 1
                column += 1
                continue
            if ch == ".":
                tokens.append(Token("DOT", ".", line_no, column))
                i += 1
                column += 1
                continue
            if ch == "(":
                tokens.append(Token("LPAREN", "(", line_no, column))
                i += 1
                column += 1
                continue
            if ch == ")":
                tokens.append(Token("RPAREN", ")", line_no, column))
                i += 1
                column += 1
                continue
            if ch == '"':
                value, consumed = self._read_string(text[i:], line_no, column)
                tokens.append(Token("STRING", value, line_no, column))
                i += consumed
                column += consumed
                continue
            if ch.isdigit():
                value, consumed = self._read_number(text[i:])
                tokens.append(Token("NUMBER", value, line_no, column))
                i += consumed
                column += consumed
                continue
            if ch.isalpha() or ch == "_":
                value, consumed = self._read_identifier(text[i:])
                token_type = KEYWORDS.get(value, "IDENT")
                token_value = self._keyword_value(token_type, value)
                tokens.append(Token(token_type, token_value, line_no, column))
                i += consumed
                column += consumed
                continue

            raise Namel3ssError(f"Unexpected character '{ch}'", line=line_no, column=column)

        return tokens

    @staticmethod
    def _read_string(text: str, line: int, column: int) -> tuple[str, int]:
        assert text[0] == '"'
        value_chars = []
        i = 1
        while i < len(text):
            ch = text[i]
            if ch == '"':
                return "".join(value_chars), i + 1
            value_chars.append(ch)
            i += 1
        raise Namel3ssError("Unterminated string literal", line=line, column=column)

    @staticmethod
    def _read_number(text: str) -> tuple[int, int]:
        i = 0
        digits = []
        while i < len(text) and text[i].isdigit():
            digits.append(text[i])
            i += 1
        return int("".join(digits)), i

    @staticmethod
    def _read_identifier(text: str) -> tuple[str, int]:
        i = 0
        chars = []
        while i < len(text) and (text[i].isalnum() or text[i] == "_"):
            chars.append(text[i])
            i += 1
        return "".join(chars), i

    @staticmethod
    def _keyword_value(token_type: str, raw: str):
        if token_type == "BOOLEAN":
            return raw.lower() == "true"
        return raw

