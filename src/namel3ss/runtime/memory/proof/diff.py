from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiffEntry:
    what: str
    where: str
    why: str
    fix: str


@dataclass(frozen=True)
class DiffResult:
    ok: bool
    entries: list[DiffEntry]

    def as_dict(self) -> dict:
        return {"ok": self.ok, "entries": [entry.__dict__ for entry in self.entries]}


def diff_scenario(current: dict, golden: dict) -> DiffResult:
    entries: list[DiffEntry] = []
    _diff_recall_steps(current.get("recall_steps") or [], golden.get("recall_steps") or [], entries)
    _diff_write_steps(current.get("write_steps") or [], golden.get("write_steps") or [], entries)
    _diff_cache_versions(current, golden, entries)
    _diff_phase_snapshots(current, golden, entries)
    return DiffResult(ok=not entries, entries=entries)


def _diff_recall_steps(current: list[dict], golden: list[dict], entries: list[DiffEntry]) -> None:
    if len(current) != len(golden):
        entries.append(
            DiffEntry(
                what="Recall step count changed.",
                where="recall steps",
                why=f"count {len(golden)} -> {len(current)}",
                fix="If intended, rerun `n3 memory proof generate`. Otherwise, fix memory logic.",
            )
        )
        return
    for idx, (cur, gold) in enumerate(zip(current, golden), start=1):
        if _compare_recall_counts(idx, cur, gold, entries):
            return
        if _compare_field(
            idx,
            cur.get("deterministic_hash"),
            gold.get("deterministic_hash"),
            entries,
            what="Recall hash changed.",
            why_label="deterministic_hash",
            step_kind="recall",
        ):
            return
        cur_phase = _phase_id(cur.get("meta"))
        gold_phase = _phase_id(gold.get("meta"))
        if cur_phase != gold_phase:
            entries.append(
                DiffEntry(
                    what="Phase meta changed.",
                    where=f"step {idx} (recall)",
                    why=f"current_phase.id {gold_phase} -> {cur_phase}",
                    fix="If intended, rerun `n3 memory proof generate`. Otherwise, fix phase handling.",
                )
            )
            return


def _compare_recall_counts(idx: int, cur: dict, gold: dict, entries: list[DiffEntry]) -> bool:
    cur_ctx = cur.get("context") or {}
    gold_ctx = gold.get("context") or {}
    for key in ("short_term", "semantic", "profile"):
        cur_count = len(cur_ctx.get(key) or [])
        gold_count = len(gold_ctx.get(key) or [])
        if cur_count != gold_count:
            entries.append(
                DiffEntry(
                    what="Recall context changed.",
                    where=f"step {idx} (recall)",
                    why=f"{key}.count {gold_count} -> {cur_count}",
                    fix="If intended, rerun `n3 memory proof generate`. Otherwise, fix recall logic.",
                )
            )
            return True
    return False


def _diff_write_steps(current: list[dict], golden: list[dict], entries: list[DiffEntry]) -> None:
    if len(current) != len(golden):
        entries.append(
            DiffEntry(
                what="Write step count changed.",
                where="write steps",
                why=f"count {len(golden)} -> {len(current)}",
                fix="If intended, rerun `n3 memory proof generate`. Otherwise, fix memory logic.",
            )
        )
        return
    for idx, (cur, gold) in enumerate(zip(current, golden), start=1):
        cur_written = len(cur.get("written") or [])
        gold_written = len(gold.get("written") or [])
        if cur_written != gold_written:
            entries.append(
                DiffEntry(
                    what="Write output changed.",
                    where=_step_label(idx, cur),
                    why=f"written.count {gold_written} -> {cur_written}",
                    fix="If intended, rerun `n3 memory proof generate`. Otherwise, fix write logic.",
                )
            )
            return
        cur_events = len(cur.get("events") or [])
        gold_events = len(gold.get("events") or [])
        if cur_events != gold_events:
            entries.append(
                DiffEntry(
                    what="Write events changed.",
                    where=_step_label(idx, cur),
                    why=f"events.count {gold_events} -> {cur_events}",
                    fix="If intended, rerun `n3 memory proof generate`. Otherwise, fix governance events.",
                )
            )
            return


def _diff_cache_versions(current: dict, golden: dict, entries: list[DiffEntry]) -> None:
    cur_steps = current.get("meta", {}).get("cache_versions_by_step") or []
    gold_steps = golden.get("meta", {}).get("cache_versions_by_step") or []
    if len(cur_steps) != len(gold_steps):
        entries.append(
            DiffEntry(
                what="Cache version steps changed.",
                where="meta.cache_versions_by_step",
                why=f"count {len(gold_steps)} -> {len(cur_steps)}",
                fix="If intended, rerun `n3 memory proof generate`. Otherwise, fix cache tracking.",
            )
        )
        return
    activity = _step_activity_map(current)
    for idx, (cur, gold) in enumerate(zip(cur_steps, gold_steps), start=1):
        cur_versions = _versions_map(cur.get("versions") or [])
        gold_versions = _versions_map(gold.get("versions") or [])
        for key, gold_version in gold_versions.items():
            cur_version = cur_versions.get(key)
            if cur_version != gold_version:
                suffix = " without a write" if not activity.get(idx, False) else ""
                entries.append(
                    DiffEntry(
                        what="Cache version changed unexpectedly.",
                        where=f"step {idx}",
                        why=f"{key} {gold_version} -> {cur_version}{suffix}",
                        fix="If intended, rerun `n3 memory proof generate`. Otherwise, fix cache versioning.",
                    )
                )
                return


def _diff_phase_snapshots(current: dict, golden: dict, entries: list[DiffEntry]) -> None:
    cur_steps = current.get("meta", {}).get("phase_snapshots_by_step") or []
    gold_steps = golden.get("meta", {}).get("phase_snapshots_by_step") or []
    if len(cur_steps) != len(gold_steps):
        entries.append(
            DiffEntry(
                what="Phase snapshot steps changed.",
                where="meta.phase_snapshots_by_step",
                why=f"count {len(gold_steps)} -> {len(cur_steps)}",
                fix="If intended, rerun `n3 memory proof generate`. Otherwise, fix phase tracking.",
            )
        )
        return
    for cur, gold in zip(cur_steps, gold_steps):
        step_index = cur.get("step_index")
        cur_map = _phases_map(cur.get("phases") or [])
        gold_map = _phases_map(gold.get("phases") or [])
        for store_key, gold_phase in gold_map.items():
            cur_phase = cur_map.get(store_key)
            if cur_phase != gold_phase:
                entries.append(
                    DiffEntry(
                        what="Phase meta changed.",
                        where=_step_label(step_index, _find_step(current, step_index)),
                        why=f"{store_key}.current {gold_phase} -> {cur_phase}",
                        fix="If intended, rerun `n3 memory proof generate`. Otherwise, fix phase handling.",
                    )
                )
                return


def _compare_field(idx: int, current: object, golden: object, entries: list[DiffEntry], *, what: str, why_label: str, step_kind: str) -> bool:
    if current == golden:
        return False
    entries.append(
        DiffEntry(
            what=what,
            where=f"step {idx} ({step_kind})",
            why=f"{why_label} {golden} -> {current}",
            fix="If intended, rerun `n3 memory proof generate`. Otherwise, fix memory logic.",
        )
    )
    return True


def _phase_id(meta: dict | None) -> str | None:
    if not isinstance(meta, dict):
        return None
    current = meta.get("current_phase")
    if not isinstance(current, dict):
        return None
    return current.get("phase_id")


def _step_label(idx: int, step: dict) -> str:
    kind = step.get("step_kind") or "write"
    if kind == "admin":
        action = step.get("action") or "admin"
        return f"step {idx} (admin:{action})"
    return f"step {idx} ({kind})"


def _step_activity_map(bundle: dict) -> dict[int, bool]:
    activity: dict[int, bool] = {}
    for step in (bundle.get("recall_steps") or []) + (bundle.get("write_steps") or []):
        idx = step.get("step_index")
        events = step.get("events") or []
        wrote = bool(step.get("written"))
        deleted = any(event.get("type") in {"memory_deleted", "memory_forget"} for event in events)
        activity[idx] = bool(wrote or deleted)
    return activity


def _find_step(bundle: dict, step_index: int) -> dict:
    for step in (bundle.get("recall_steps") or []) + (bundle.get("write_steps") or []):
        if step.get("step_index") == step_index:
            return step
    return {"step_kind": "step"}


def _versions_map(entries: list[dict]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for entry in entries:
        key = f"{entry.get('store_key')}:{entry.get('kind')}"
        mapping[key] = int(entry.get("version", 0))
    return mapping


def _phases_map(entries: list[dict]) -> dict[str, str | None]:
    mapping: dict[str, str | None] = {}
    for entry in entries:
        store_key = entry.get("store_key")
        mapping[str(store_key)] = entry.get("current_phase_id")
    return mapping


__all__ = ["DiffEntry", "DiffResult", "diff_scenario"]
