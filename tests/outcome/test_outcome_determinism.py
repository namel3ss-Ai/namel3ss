from __future__ import annotations

from pathlib import Path

from namel3ss.outcome.builder import build_outcome_pack
from namel3ss.outcome.model import MemoryOutcome, StateOutcome, StoreOutcome


def _build(tmp_path: Path) -> tuple[str, str]:
    store = StoreOutcome(began=True, committed=True, commit_failed=False, rolled_back=False, rollback_failed=False)
    state = StateOutcome(loaded_from_store=False, save_attempted=True, save_succeeded=True, save_failed=False)
    memory = MemoryOutcome(persist_attempted=True, persist_succeeded=True, persist_failed=False, skipped_reason=None)
    build_outcome_pack(
        flow_name="demo",
        store=store,
        state=state,
        memory=memory,
        record_changes_count=0,
        execution_steps_count=2,
        traces_count=1,
        error_escaped=False,
        project_root=tmp_path,
    )
    outcome_dir = tmp_path / ".namel3ss" / "outcome"
    json_text = (outcome_dir / "last.json").read_text(encoding="utf-8")
    plain_text = (outcome_dir / "last.plain").read_text(encoding="utf-8")
    return json_text, plain_text


def test_outcome_deterministic(tmp_path: Path) -> None:
    first_json, first_plain = _build(tmp_path)
    second_json, second_plain = _build(tmp_path)
    assert first_json == second_json
    assert first_plain == second_plain
    assert "- none recorded" in first_plain
