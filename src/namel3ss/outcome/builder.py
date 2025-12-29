from __future__ import annotations

from pathlib import Path

from namel3ss.outcome.model import MemoryOutcome, OutcomePack, RunOutcome, StateOutcome, StoreOutcome
from namel3ss.outcome.normalize import normalize_outcome, write_outcome_artifacts
from namel3ss.outcome.render_plain import render_what


def build_outcome_pack(
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
) -> OutcomePack:
    status = _derive_status(store, state, memory, error_escaped)
    what_did_not_happen = _what_did_not_happen(store, state, memory)

    outcome = RunOutcome(
        status=status,
        flow_name=flow_name,
        store=store,
        state=state,
        memory=memory,
        record_changes_count=record_changes_count,
        execution_steps_count=execution_steps_count,
        traces_count=traces_count,
        what_did_not_happen=what_did_not_happen,
    )
    normalized = normalize_outcome(outcome)
    summary = {
        "status": normalized.status,
        "flow_name": normalized.flow_name,
        "store": normalized.store.as_dict(),
        "memory": normalized.memory.as_dict(),
    }
    pack = OutcomePack(outcome=normalized, summary=summary)

    root = _resolve_root(project_root)
    if root is not None:
        plain_text = render_what(pack)
        try:
            write_outcome_artifacts(root, pack, plain_text, plain_text)
        except Exception:
            pass

    return pack


def _derive_status(store: StoreOutcome, state: StateOutcome, memory: MemoryOutcome, error_escaped: bool) -> str:
    if error_escaped:
        return "error"
    if store.commit_failed or store.rollback_failed or state.save_failed or memory.persist_failed:
        return "partial"
    return "ok"


def _what_did_not_happen(store: StoreOutcome, state: StateOutcome, memory: MemoryOutcome) -> tuple[str, ...]:
    bullets: list[str] = []

    if store.commit_failed:
        bullets.append("store commit did not complete successfully")
    elif not store.committed:
        bullets.append("store commit was not attempted")

    if store.rollback_failed:
        bullets.append("rollback did not complete successfully")

    if state.save_failed:
        bullets.append("state save did not complete successfully")
    elif not state.save_attempted:
        bullets.append("state was not saved")

    if memory.persist_failed:
        bullets.append("memory persistence did not complete successfully")
    elif not memory.persist_attempted:
        bullets.append("memory was not persisted")

    return tuple(bullets)


def _resolve_root(project_root: str | Path | None) -> Path | None:
    if isinstance(project_root, Path):
        return project_root
    if isinstance(project_root, str) and project_root:
        return Path(project_root)
    return Path.cwd()


__all__ = ["build_outcome_pack"]
