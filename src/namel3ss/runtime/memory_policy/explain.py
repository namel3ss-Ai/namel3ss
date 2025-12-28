from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory_policy.evaluation import ConflictDecision, PolicyDecision


def explain_write_decision(decision: PolicyDecision, *, kind: str, event_type: str) -> dict:
    return {
        "allowed": decision.allowed,
        "reason": decision.reason,
        "tags": list(decision.tags),
        "kind": kind,
        "event_type": event_type,
    }


def explain_conflict(decision: ConflictDecision) -> dict:
    winner = decision.winner
    loser = decision.loser
    return {
        "rule": decision.rule,
        "authority": {
            "winner": winner.meta.get("authority"),
            "loser": loser.meta.get("authority"),
        },
        "event_type": {
            "winner": winner.meta.get("event_type"),
            "loser": loser.meta.get("event_type"),
        },
        "recency": {
            "winner_created_at": winner.created_at,
            "loser_created_at": loser.created_at,
        },
        "importance": {
            "winner": winner.importance,
            "loser": loser.importance,
        },
    }


def explain_forget(item: MemoryItem, *, reason: str) -> dict:
    return {
        "reason": reason,
        "kind": item.kind.value if hasattr(item.kind, "value") else str(item.kind),
        "event_type": item.meta.get("event_type"),
        "authority": item.meta.get("authority"),
    }


__all__ = ["explain_conflict", "explain_forget", "explain_write_decision"]
