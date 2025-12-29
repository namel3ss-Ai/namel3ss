from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from namel3ss.runtime.memory.contract import deterministic_recall_hash, validate_memory_item
from namel3ss.runtime.memory.spaces import validate_space_rules
from namel3ss.runtime.memory_lanes.model import validate_lane_rules

from .runner import ScenarioRun


@dataclass(frozen=True)
class InvariantReport:
    ok: bool
    failures: list[dict]
    notes: list[str]

    def as_dict(self) -> dict:
        return {"ok": self.ok, "failures": list(self.failures), "notes": list(self.notes)}


def check_invariants(run: ScenarioRun) -> InvariantReport:
    failures: list[dict] = []
    notes: list[str] = []
    _check_determinism(run, failures)
    _check_contract_shape(run, failures)
    _check_lane_isolation(run, failures)
    _check_cache_versions(run, failures)
    _check_deletion_explanations(run, failures, notes)
    return InvariantReport(ok=not failures, failures=failures, notes=notes)


def _check_determinism(run: ScenarioRun, failures: list[dict]) -> None:
    for step in run.recall_steps:
        items = _flatten_context(step.get("context") or {})
        expected = step.get("deterministic_hash")
        actual = deterministic_recall_hash(items)
        if expected != actual:
            failures.append(
                {
                    "check": "determinism",
                    "step_index": step.get("step_index"),
                    "message": "Recall hash does not match recalled items.",
                    "expected": expected,
                    "actual": actual,
                }
            )


def _check_contract_shape(run: ScenarioRun, failures: list[dict]) -> None:
    for step in run.write_steps:
        for item in step.get("written") or []:
            try:
                validate_memory_item(item)
                validate_space_rules(item)
                validate_lane_rules(item)
            except Exception as exc:  # pragma: no cover - defensive
                failures.append(
                    {
                        "check": "contract_shape",
                        "step_index": step.get("step_index"),
                        "message": str(exc),
                        "memory_id": item.get("id") if isinstance(item, dict) else None,
                    }
                )


def _check_lane_isolation(run: ScenarioRun, failures: list[dict]) -> None:
    for step in run.write_steps:
        for item in step.get("written") or []:
            memory_id = item.get("id") if isinstance(item, dict) else None
            store_key, _kind = _parse_memory_id(memory_id)
            if not store_key:
                continue
            lane = _lane_from_store_key(store_key)
            meta = item.get("meta") if isinstance(item, dict) else {}
            item_lane = meta.get("lane") if isinstance(meta, dict) else None
            if lane and item_lane and lane.startswith("agent:") and item_lane != "agent":
                failures.append(
                    {
                        "check": "lane_isolation",
                        "step_index": step.get("step_index"),
                        "message": "Agent lane item stored with non-agent lane metadata.",
                        "memory_id": memory_id,
                    }
                )
            if item_lane == "agent" and (not lane or not lane.startswith("agent:")):
                failures.append(
                    {
                        "check": "lane_isolation",
                        "step_index": step.get("step_index"),
                        "message": "Agent lane metadata stored outside an agent lane store.",
                        "memory_id": memory_id,
                    }
                )
            if lane and lane.startswith("agent:") and item_lane == "agent":
                lane_agent_id = lane.split("agent:", 1)[1]
                meta_agent_id = meta.get("agent_id") if isinstance(meta, dict) else None
                if meta_agent_id and str(meta_agent_id) != lane_agent_id:
                    failures.append(
                        {
                            "check": "lane_isolation",
                            "step_index": step.get("step_index"),
                            "message": "Agent lane agent_id does not match store key.",
                            "memory_id": memory_id,
                        }
                    )
            if lane == "team" and item_lane == "agent":
                failures.append(
                    {
                        "check": "lane_isolation",
                        "step_index": step.get("step_index"),
                        "message": "Agent lane metadata found in team lane store.",
                        "memory_id": memory_id,
                    }
                )


def _check_cache_versions(run: ScenarioRun, failures: list[dict]) -> None:
    steps = run.meta.get("cache_versions_by_step") or []
    if not steps:
        return
    previous: dict[tuple[str, str], int] = {}
    step_activity = _step_activity_map(run)
    for entry in steps:
        step_index = entry.get("step_index")
        current_versions = _versions_to_map(entry.get("versions") or [])
        for key, version in current_versions.items():
            prior = previous.get(key)
            if prior is not None and version < prior:
                failures.append(
                    {
                        "check": "cache_version",
                        "step_index": step_index,
                        "message": "Cache version decreased between steps.",
                        "key": f"{key[0]}:{key[1]}",
                        "previous": prior,
                        "current": version,
                    }
                )
            if prior is not None and version > prior and not step_activity.get(step_index, False):
                failures.append(
                    {
                        "check": "cache_version",
                        "step_index": step_index,
                        "message": "Cache version changed without a write or delete.",
                        "key": f"{key[0]}:{key[1]}",
                        "previous": prior,
                        "current": version,
                    }
                )
        previous = current_versions


def _check_deletion_explanations(run: ScenarioRun, failures: list[dict], notes: list[str]) -> None:
    deletion_events = []
    for step in run.recall_steps + run.write_steps:
        deletion_events.extend([event for event in step.get("events") or [] if event.get("type") == "memory_deleted"])
    if not deletion_events:
        return
    has_explanation = any("explanation" in event for event in deletion_events)
    if not has_explanation:
        notes.append("TODO: memory_deleted explanation field is not emitted yet.")
        return
    for event in deletion_events:
        if not event.get("explanation"):
            failures.append(
                {
                    "check": "deletion_explanation",
                    "message": "memory_deleted event missing explanation.",
                    "memory_id": event.get("memory_id"),
                }
            )


def _flatten_context(context: dict) -> list[dict]:
    return list(context.get("short_term", [])) + list(context.get("semantic", [])) + list(context.get("profile", []))


def _step_activity_map(run: ScenarioRun) -> dict[int, bool]:
    activity: dict[int, bool] = {}
    for step in run.recall_steps + run.write_steps:
        step_index = step.get("step_index")
        events = step.get("events") or []
        wrote = bool(step.get("written"))
        deleted = any(event.get("type") in {"memory_deleted", "memory_forget"} for event in events)
        activity[step_index] = bool(wrote or deleted)
    return activity


def _versions_to_map(entries: Iterable[dict]) -> dict[tuple[str, str], int]:
    mapping: dict[tuple[str, str], int] = {}
    for entry in entries:
        store_key = str(entry.get("store_key"))
        kind = str(entry.get("kind"))
        version = int(entry.get("version", 0))
        mapping[(store_key, kind)] = version
    return mapping


def _parse_memory_id(value: object) -> tuple[str | None, str | None]:
    if not isinstance(value, str):
        return None, None
    parts = value.split(":")
    if len(parts) < 3:
        return None, None
    store_key = ":".join(parts[:-2])
    kind = parts[-2]
    return store_key, kind


def _lane_from_store_key(store_key: str) -> str | None:
    parts = store_key.split(":")
    if len(parts) < 3:
        return None
    return ":".join(parts[2:])


__all__ = ["InvariantReport", "check_invariants"]
