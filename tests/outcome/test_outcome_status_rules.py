from __future__ import annotations

from namel3ss.outcome.builder import build_outcome_pack
from namel3ss.outcome.model import MemoryOutcome, StateOutcome, StoreOutcome


def _base_store() -> StoreOutcome:
    return StoreOutcome(began=True, committed=True, commit_failed=False, rolled_back=False, rollback_failed=False)


def _base_state() -> StateOutcome:
    return StateOutcome(loaded_from_store=None, save_attempted=True, save_succeeded=True, save_failed=False)


def test_partial_outcome_memory_failure(tmp_path) -> None:
    store = _base_store()
    state = _base_state()
    memory = MemoryOutcome(persist_attempted=True, persist_succeeded=False, persist_failed=True, skipped_reason=None)
    pack = build_outcome_pack(
        flow_name="demo",
        store=store,
        state=state,
        memory=memory,
        record_changes_count=0,
        execution_steps_count=0,
        traces_count=0,
        error_escaped=False,
        project_root=tmp_path,
    )
    assert pack.outcome.status == "partial"
    assert "memory persistence did not complete successfully" in pack.outcome.what_did_not_happen


def test_error_outcome_when_exception_escaped(tmp_path) -> None:
    store = StoreOutcome(began=True, committed=False, commit_failed=False, rolled_back=False, rollback_failed=False)
    state = StateOutcome(loaded_from_store=True, save_attempted=False, save_succeeded=False, save_failed=False)
    memory = MemoryOutcome(persist_attempted=False, persist_succeeded=False, persist_failed=False, skipped_reason=None)
    pack = build_outcome_pack(
        flow_name="demo",
        store=store,
        state=state,
        memory=memory,
        record_changes_count=0,
        execution_steps_count=0,
        traces_count=0,
        error_escaped=True,
        project_root=tmp_path,
    )
    assert pack.outcome.status == "error"
    assert "store commit was not attempted" in pack.outcome.what_did_not_happen
    assert "state was not saved" in pack.outcome.what_did_not_happen
    assert "memory was not persisted" in pack.outcome.what_did_not_happen
