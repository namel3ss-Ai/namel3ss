from __future__ import annotations

import json
from pathlib import Path

from namel3ss.outcome.builder import build_outcome_pack
from namel3ss.outcome.model import MemoryOutcome, OutcomePack, RunOutcome, StateOutcome, StoreOutcome
from namel3ss.outcome.render_plain import render_what


def build_run_outcome(
    *,
    flow_name: str,
    store: StoreOutcome,
    state: StateOutcome,
    memory: MemoryOutcome,
    record_changes_count: int,
    execution_steps_count: int,
    traces_count: int,
    error_escaped: bool,
    project_root: str | Path | None = None,
) -> tuple[OutcomePack, str]:
    pack = build_outcome_pack(
        flow_name=flow_name,
        store=store,
        state=state,
        memory=memory,
        record_changes_count=record_changes_count,
        execution_steps_count=execution_steps_count,
        traces_count=traces_count,
        error_escaped=error_escaped,
        project_root=project_root,
    )
    return pack, render_what(pack)


def load_outcome_pack(path: Path) -> OutcomePack | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    outcome_data = payload.get("outcome")
    if not isinstance(outcome_data, dict):
        return None
    store = _store_from_dict(outcome_data.get("store"))
    state = _state_from_dict(outcome_data.get("state"))
    memory = _memory_from_dict(outcome_data.get("memory"))
    if store is None or state is None or memory is None:
        return None
    what = outcome_data.get("what_did_not_happen") or []
    if not isinstance(what, list):
        return None
    run_outcome = RunOutcome(
        status=str(outcome_data.get("status") or ""),
        flow_name=str(outcome_data.get("flow_name") or ""),
        store=store,
        state=state,
        memory=memory,
        record_changes_count=int(outcome_data.get("record_changes_count") or 0),
        execution_steps_count=int(outcome_data.get("execution_steps_count") or 0),
        traces_count=int(outcome_data.get("traces_count") or 0),
        what_did_not_happen=tuple(str(item) for item in what if item is not None),
    )
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return OutcomePack(outcome=run_outcome, summary=summary)


def _store_from_dict(value: object) -> StoreOutcome | None:
    if not isinstance(value, dict):
        return None
    try:
        return StoreOutcome(
            began=bool(value.get("began")),
            committed=bool(value.get("committed")),
            commit_failed=bool(value.get("commit_failed")),
            rolled_back=bool(value.get("rolled_back")),
            rollback_failed=bool(value.get("rollback_failed")),
        )
    except Exception:
        return None


def _state_from_dict(value: object) -> StateOutcome | None:
    if not isinstance(value, dict):
        return None
    loaded = value.get("loaded_from_store")
    loaded_from_store = loaded if isinstance(loaded, bool) else None
    try:
        return StateOutcome(
            loaded_from_store=loaded_from_store,
            save_attempted=bool(value.get("save_attempted")),
            save_succeeded=bool(value.get("save_succeeded")),
            save_failed=bool(value.get("save_failed")),
        )
    except Exception:
        return None


def _memory_from_dict(value: object) -> MemoryOutcome | None:
    if not isinstance(value, dict):
        return None
    skipped = value.get("skipped_reason")
    skipped_reason = str(skipped) if isinstance(skipped, str) and skipped else None
    try:
        return MemoryOutcome(
            persist_attempted=bool(value.get("persist_attempted")),
            persist_succeeded=bool(value.get("persist_succeeded")),
            persist_failed=bool(value.get("persist_failed")),
            skipped_reason=skipped_reason,
        )
    except Exception:
        return None


__all__ = ["build_run_outcome", "load_outcome_pack"]
