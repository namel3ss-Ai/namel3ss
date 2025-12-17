from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Reserved words mapped to their token types. Keep each keyword string once to
# avoid silent overrides; duplicates hide earlier entries and break coverage.
# When adding new keywords, append here only after confirming the token type is
# unique and tests cover the new surface.
KEYWORDS = {
    "flow": "FLOW",
    "page": "PAGE",
    "ai": "AI",
    "ask": "ASK",
    "with": "WITH",
    "input": "INPUT",
    "as": "AS",
    "provider": "PROVIDER",
    "tools": "TOOLS",
    "expose": "EXPOSE",
    "tool": "TOOL",
    "kind": "KIND",
    "memory": "MEMORY",
    "short_term": "SHORT_TERM",
    "semantic": "SEMANTIC",
    "profile": "PROFILE",
    "agent": "AGENT",
    "agents": "AGENTS",
    "parallel": "PARALLEL",
    "run": "RUN",
    "model": "MODEL",
    "system_prompt": "SYSTEM_PROMPT",
    "title": "TITLE",
    "text": "TEXT",
    "form": "FORM",
    "table": "TABLE",
    "button": "BUTTON",
    "calls": "CALLS",
    "record": "RECORD",
    "save": "SAVE",
    "find": "FIND",
    "where": "WHERE",
    "let": "LET",
    "set": "SET",
    "return": "RETURN",
    "repeat": "REPEAT",
    "up": "UP",
    "to": "TO",
    "times": "TIMES",
    "for": "FOR",
    "each": "EACH",
    "in": "IN",
    "match": "MATCH",
    "when": "WHEN",
    "otherwise": "OTHERWISE",
    "try": "TRY",
    "catch": "CATCH",
    "if": "IF",
    "else": "ELSE",
    "is": "IS",
    "greater": "GREATER",
    "less": "LESS",
    "equal": "EQUAL",
    "than": "THAN",
    "and": "AND",
    "or": "OR",
    "not": "NOT",
    "state": "STATE",
    "constant": "CONSTANT",
    "true": "BOOLEAN",
    "false": "BOOLEAN",
    "string": "TYPE_STRING",
    "int": "TYPE_INT",
    "number": "TYPE_NUMBER",
    "boolean": "TYPE_BOOLEAN",
    "json": "TYPE_JSON",
    "must": "MUST",
    "be": "BE",
    "present": "PRESENT",
    "unique": "UNIQUE",
    "pattern": "PATTERN",
    "have": "HAVE",
    "length": "LENGTH",
    "at": "AT",
    "least": "LEAST",
    "most": "MOST",
}


@dataclass(frozen=True)
class Token:
    type: str
    value: Optional[object]
    line: int
    column: int

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Token({self.type}, {self.value}, {self.line}:{self.column})"
