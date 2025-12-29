from __future__ import annotations

from typing import Iterable

from namel3ss.runtime.tools.explain.decision import ToolDecision


def expected_effects_from_steps(steps: list[dict]) -> list[str]:
    effects: list[str] = []
    if _has_step_kind(steps, "tool_call"):
        effects.append("may call tools")
    if _has_step_kind(steps, "statement_save") or _has_step_kind(steps, "statement_create"):
        effects.append("may write records")
    return effects


def expected_effects_from_tools(decisions: list[ToolDecision]) -> list[str]:
    if decisions:
        return ["may call tools"]
    return []


def expected_effects_from_memory(memory_pack: dict | None) -> list[str]:
    count = memory_write_count(memory_pack)
    if count and count > 0:
        return ["may write memory"]
    return []


def summarize_tool_decisions(decisions: list[ToolDecision]) -> dict:
    counts = {"total": len(decisions), "ok": 0, "blocked": 0, "error": 0}
    for decision in decisions:
        if decision.status == "ok":
            counts["ok"] += 1
        elif decision.status == "blocked":
            counts["blocked"] += 1
        elif decision.status == "error":
            counts["error"] += 1
    return counts


def summarize_memory(memory_pack: dict | None) -> dict:
    count = memory_write_count(memory_pack)
    if count is None:
        return {}
    return {"written": count}


def memory_write_count(memory_pack: dict | None) -> int | None:
    if not isinstance(memory_pack, dict):
        return None
    proof = memory_pack.get("proof")
    if isinstance(proof, dict) and proof.get("write_count") is not None:
        try:
            return int(proof.get("write_count"))
        except (TypeError, ValueError):
            return None
    summary = memory_pack.get("summary")
    if isinstance(summary, str) and summary.startswith("Recorded "):
        parts = summary.split()
        if len(parts) >= 2:
            try:
                return int(parts[1])
            except ValueError:
                return None
    payload = memory_pack.get("payload")
    if isinstance(payload, list):
        return len(payload)
    return None


def _has_step_kind(steps: list[dict], kind: str) -> bool:
    return any(step.get("kind") == kind for step in steps if isinstance(step, dict))


def unique_items(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


__all__ = [
    "expected_effects_from_steps",
    "expected_effects_from_tools",
    "expected_effects_from_memory",
    "memory_write_count",
    "summarize_memory",
    "summarize_tool_decisions",
    "unique_items",
]
