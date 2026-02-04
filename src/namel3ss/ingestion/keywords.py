from __future__ import annotations

import re

MIN_KEYWORD_LENGTH = 3
MAX_KEYWORDS = 16

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "no",
    "not",
    "of",
    "on",
    "or",
    "such",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "they",
    "this",
    "to",
    "was",
    "will",
    "with",
    "you",
    "your",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def extract_keywords(text: str, *, max_keywords: int = MAX_KEYWORDS) -> list[str]:
    if not isinstance(text, str) or not text:
        return []
    tokens = _TOKEN_RE.findall(text.lower())
    keywords: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if len(token) < MIN_KEYWORD_LENGTH:
            continue
        if token in _STOPWORDS:
            continue
        if token in seen:
            continue
        seen.add(token)
        keywords.append(token)
        if len(keywords) >= max_keywords:
            break
    return keywords


def normalize_keywords(value: object, *, max_keywords: int = MAX_KEYWORDS) -> list[str] | None:
    if not isinstance(value, list):
        return None
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            return None
        token = item.strip().lower()
        if not token:
            return None
        if token in seen:
            continue
        seen.add(token)
        normalized.append(token)
        if len(normalized) >= max_keywords:
            break
    return normalized


def keyword_matches(query_keywords: list[str], chunk_keywords: list[str]) -> list[str]:
    if not query_keywords or not chunk_keywords:
        return []
    chunk_set = set(chunk_keywords)
    return [keyword for keyword in query_keywords if keyword in chunk_set]


__all__ = [
    "MAX_KEYWORDS",
    "MIN_KEYWORD_LENGTH",
    "extract_keywords",
    "keyword_matches",
    "normalize_keywords",
]
