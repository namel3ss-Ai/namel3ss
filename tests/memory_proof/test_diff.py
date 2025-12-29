from namel3ss.runtime.memory.proof.diff import diff_scenario


def test_diff_reports_recall_change() -> None:
    golden = {
        "recall_steps": [
            {
                "step_index": 1,
                "step_kind": "recall",
                "context": {"semantic": ["a", "b"], "short_term": [], "profile": []},
                "deterministic_hash": "hash-a",
                "meta": {"current_phase": {"phase_id": "phase-1"}},
            }
        ],
        "write_steps": [],
        "meta": {"cache_versions_by_step": []},
    }
    current = {
        "recall_steps": [
            {
                "step_index": 1,
                "step_kind": "recall",
                "context": {"semantic": ["a"], "short_term": [], "profile": []},
                "deterministic_hash": "hash-a",
                "meta": {"current_phase": {"phase_id": "phase-1"}},
            }
        ],
        "write_steps": [],
        "meta": {"cache_versions_by_step": []},
    }
    result = diff_scenario(current, golden)
    assert not result.ok
    assert result.entries
    assert result.entries[0].what == "Recall context changed."
