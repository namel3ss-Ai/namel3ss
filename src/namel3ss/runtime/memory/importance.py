from __future__ import annotations

from namel3ss.runtime.memory.events import (
    EVENT_CONTEXT,
    EVENT_CORRECTION,
    EVENT_DECISION,
    EVENT_EXECUTION,
    EVENT_FACT,
    EVENT_PREFERENCE,
    EVENT_RULE,
)

_BASE_IMPORTANCE = {
    EVENT_PREFERENCE: 3,
    EVENT_DECISION: 3,
    EVENT_RULE: 4,
    EVENT_FACT: 4,
    EVENT_CORRECTION: 4,
    EVENT_EXECUTION: 2,
    EVENT_CONTEXT: 1,
}

_EMPHASIS_MARKERS = ("always", "never", "must", "avoid")


def importance_for_event(event_type: str, text: str, source: str) -> tuple[int, list[str]]:
    score = _BASE_IMPORTANCE.get(event_type, 0)
    reasons = [f"event:{event_type}"]
    lowered = text.lower()
    if source == "user":
        score += 1
        reasons.append("source:user")
    if any(marker in lowered for marker in _EMPHASIS_MARKERS):
        score += 1
        reasons.append("emphasis")
    if event_type == EVENT_CORRECTION:
        score += 1
        reasons.append("corrective")
    return score, reasons


__all__ = ["importance_for_event"]
