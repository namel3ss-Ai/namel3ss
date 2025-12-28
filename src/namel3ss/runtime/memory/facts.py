from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Fact:
    key: str
    value: str
    reason: str


SENSITIVE_MARKERS = (
    "password",
    "secret",
    "token",
    "api key",
    "apikey",
    "credit card",
    "ssn",
    "social security",
    "private key",
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

_FACT_PATTERNS = [
    ("name", re.compile(r"\bmy name is (?P<value>[^.!?,;]+)", re.IGNORECASE)),
    ("name", re.compile(r"\bcall me (?P<value>[^.!?,;]+)", re.IGNORECASE)),
    ("timezone", re.compile(r"\bmy timezone is (?P<value>[^.!?,;]+)", re.IGNORECASE)),
    ("timezone", re.compile(r"\btimezone (is|=) (?P<value>[^.!?,;]+)", re.IGNORECASE)),
    ("language", re.compile(r"\bmy language is (?P<value>[^.!?,;]+)", re.IGNORECASE)),
    ("language", re.compile(r"\blanguage preference is (?P<value>[^.!?,;]+)", re.IGNORECASE)),
    ("project", re.compile(r"\bmy project (is|name is) (?P<value>[^.!?,;]+)", re.IGNORECASE)),
    ("project", re.compile(r"\bworking on (?P<value>[^.!?,;]+)", re.IGNORECASE)),
    ("editor", re.compile(r"\bmy editor is (?P<value>[^.!?,;]+)", re.IGNORECASE)),
    ("units", re.compile(r"\buse (?P<value>metric|imperial) units\b", re.IGNORECASE)),
]

FACT_KEYS = tuple(dict.fromkeys(key for key, _ in _FACT_PATTERNS))


def extract_fact(text: str) -> Fact | None:
    if not text:
        return None
    for key, pattern in _FACT_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = _sanitize_value(match.group("value"))
        if not value:
            continue
        return Fact(key=key, value=value, reason=f"pattern:{key}")
    return None


def _sanitize_value(value: str) -> str:
    cleaned = value.strip().strip("\"'")
    cleaned = cleaned.rstrip(".!,;: ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if len(cleaned) > 60:
        cleaned = cleaned[:60].rstrip()
    return cleaned


def _is_sensitive(text: str) -> bool:
    lowered = text.lower()
    if any(marker in lowered for marker in SENSITIVE_MARKERS):
        return True
    if _EMAIL_RE.search(text):
        return True
    if _SSN_RE.search(text):
        return True
    return False


__all__ = ["FACT_KEYS", "Fact", "SENSITIVE_MARKERS", "extract_fact"]
