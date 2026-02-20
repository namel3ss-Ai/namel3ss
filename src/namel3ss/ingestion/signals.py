from __future__ import annotations

import re


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def compute_signals(text: str, *, detected: dict) -> dict:
    text = text or ""
    text_chars = len(text)
    tokens = _TOKEN_RE.findall(text.lower())
    unique_tokens = len(set(tokens))
    total_tokens = len(tokens)
    unique_token_ratio = _ratio(unique_tokens, total_tokens)
    non_ascii_ratio = _ratio(_non_ascii_count(text), text_chars)
    line_break_ratio = _ratio(text.count("\n"), text_chars)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    repeated_line_ratio = _repeated_line_ratio(lines)
    table_like_ratio = _table_like_ratio(lines)
    empty_pages_ratio = _empty_pages_ratio(text, detected.get("page_count"))
    uppercase_alpha_ratio, vowel_alpha_ratio = _alpha_ratios(text)
    return {
        "text_chars": text_chars,
        "unique_token_ratio": unique_token_ratio,
        "non_ascii_ratio": non_ascii_ratio,
        "line_break_ratio": line_break_ratio,
        "repeated_line_ratio": repeated_line_ratio,
        "table_like_ratio": table_like_ratio,
        "empty_pages_ratio": empty_pages_ratio,
        "uppercase_alpha_ratio": uppercase_alpha_ratio,
        "vowel_alpha_ratio": vowel_alpha_ratio,
    }


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)


def _non_ascii_count(text: str) -> int:
    return sum(1 for ch in text if ord(ch) > 127)


def _repeated_line_ratio(lines: list[str]) -> float:
    if not lines:
        return 0.0
    counts: dict[str, int] = {}
    for line in lines:
        counts[line] = counts.get(line, 0) + 1
    repeated = sum(1 for line in lines if counts.get(line, 0) > 1)
    return _ratio(repeated, len(lines))


def _table_like_ratio(lines: list[str]) -> float:
    if not lines:
        return 0.0
    table_lines = 0
    for line in lines:
        if "|" in line or "\t" in line:
            table_lines += 1
            continue
        if re.search(r"\\s{2,}\\S+\\s{2,}", line):
            table_lines += 1
    return _ratio(table_lines, len(lines))


def _empty_pages_ratio(text: str, page_count: object) -> float:
    if not isinstance(page_count, int) or page_count <= 0:
        return 0.0
    pages = text.split("\f")
    if len(pages) < page_count:
        pages += [""] * (page_count - len(pages))
    empties = 0
    for page in pages[:page_count]:
        if len(page.strip()) < 10:
            empties += 1
    return _ratio(empties, page_count)


def _alpha_ratios(text: str) -> tuple[float, float]:
    if not text:
        return 0.0, 0.0
    alpha = 0
    uppercase = 0
    vowels = 0
    for char in text:
        if not char.isalpha():
            continue
        alpha += 1
        if char.isupper():
            uppercase += 1
        if char.lower() in {"a", "e", "i", "o", "u"}:
            vowels += 1
    if alpha == 0:
        return 0.0, 0.0
    return round(uppercase / alpha, 6), round(vowels / alpha, 6)


__all__ = ["compute_signals"]
