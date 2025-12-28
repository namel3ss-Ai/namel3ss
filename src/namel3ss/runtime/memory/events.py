from __future__ import annotations

import re

from namel3ss.runtime.memory.facts import extract_fact

EVENT_PREFERENCE = "preference"
EVENT_DECISION = "decision"
EVENT_FACT = "fact"
EVENT_CORRECTION = "correction"
EVENT_EXECUTION = "execution"
EVENT_RULE = "rule"
EVENT_CONTEXT = "context"

EVENT_TYPES = {
    EVENT_PREFERENCE,
    EVENT_DECISION,
    EVENT_FACT,
    EVENT_CORRECTION,
    EVENT_EXECUTION,
    EVENT_RULE,
    EVENT_CONTEXT,
}

_PREFERENCE_PATTERNS = [
    re.compile(r"\bi prefer\b"),
    re.compile(r"\bi like\b"),
    re.compile(r"\bi want\b"),
    re.compile(r"\bnever (do|use|call)\b"),
]
_DECISION_PATTERNS = [
    re.compile(r"\bwe decided\b"),
    re.compile(r"\bdecision\b"),
    re.compile(r"\bdecided\b"),
    re.compile(r"\bchoose\b"),
    re.compile(r"\blet's use\b"),
    re.compile(r"\bwe will use\b"),
    re.compile(r"\buse [a-z0-9]"),
]
_CORRECTION_PATTERNS = [
    re.compile(r"\bactually\b"),
    re.compile(r"\bcorrection\b"),
    re.compile(r"\bnot\b.+\bbut\b"),
]

_LOW_SIGNAL = {
    "ok",
    "okay",
    "thanks",
    "thank you",
    "hello",
    "hi",
    "hey",
    "cool",
    "great",
}


def normalize_text(text: str) -> str:
    lowered = text.lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", lowered)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def build_dedupe_key(event_type: str, text: str) -> str:
    return f"{event_type}:{normalize_text(text)}"


def is_low_signal(text: str) -> bool:
    normalized = normalize_text(text)
    return normalized in _LOW_SIGNAL


def classify_event_type(text: str, *, has_tool_events: bool = False) -> str:
    if has_tool_events:
        return EVENT_EXECUTION
    lowered = text.lower()
    if any(pattern.search(lowered) for pattern in _CORRECTION_PATTERNS):
        return EVENT_CORRECTION
    if any(pattern.search(lowered) for pattern in _PREFERENCE_PATTERNS):
        return EVENT_PREFERENCE
    if any(pattern.search(lowered) for pattern in _DECISION_PATTERNS):
        return EVENT_DECISION
    if extract_fact(text) is not None:
        return EVENT_FACT
    return EVENT_CONTEXT


__all__ = [
    "EVENT_CONTEXT",
    "EVENT_CORRECTION",
    "EVENT_DECISION",
    "EVENT_EXECUTION",
    "EVENT_FACT",
    "EVENT_PREFERENCE",
    "EVENT_RULE",
    "EVENT_TYPES",
    "build_dedupe_key",
    "classify_event_type",
    "is_low_signal",
    "normalize_text",
]
