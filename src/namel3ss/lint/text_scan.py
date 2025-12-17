from __future__ import annotations

import re
from typing import List

from namel3ss.lint.types import Finding


LEGACY_DECL = re.compile(r'^(flow|page|record|ai|agent|tool)\s+is\s+"')
ONE_LINE_BUTTON = re.compile(r'^\s*button\s+"[^"]+"\s+calls\s+flow\s+"[^"]+"\s*$')
PAGE_HEADER = re.compile(r'^\s*page\s+"[^"]+"\s*:\s*$')
FORBIDDEN_PAGE_TOKENS = {
    "let",
    "set",
    "if",
    "match",
    "repeat",
    "for",
    "try",
    "return",
    "ask",
    "run",
    "save",
    "find",
}


def scan_text(lines: List[str]) -> List[Finding]:
    findings: List[Finding] = []
    page_indent = None
    for idx, line in enumerate(lines, start=1):
        if LEGACY_DECL.search(line):
            findings.append(
                Finding(
                    code="grammar.decl_uses_is",
                    message="Declaration uses 'is'; use: <keyword> \"name\":",
                    line=idx,
                    column=1,
                )
            )
        if ONE_LINE_BUTTON.search(line):
            findings.append(
                Finding(
                    code="ui.button_one_line_forbidden",
                    message='Buttons must use a block form: button "X": NEWLINE indent calls flow "Y"',
                    line=idx,
                    column=1,
                )
            )
        if PAGE_HEADER.match(line):
            page_indent = len(line) - len(line.lstrip(" "))
            continue
        if page_indent is not None:
            if line.strip() == "":
                continue
            current_indent = len(line) - len(line.lstrip(" "))
            if current_indent <= page_indent:
                page_indent = None
                continue
            token = line.strip().split()[0].lower()
            if token in FORBIDDEN_PAGE_TOKENS:
                findings.append(
                    Finding(
                        code="page.imperative_not_allowed",
                        message=f"Pages are declarative only; '{token}' is not allowed inside page blocks.",
                        line=idx,
                        column=current_indent + 1,
                    )
                )
    return findings
