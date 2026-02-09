from __future__ import annotations

from namel3ss.studio.diff.run_diff import RUN_DIFF_FIELD_ORDER, build_run_diff


def test_run_diff_is_deterministic_and_ordered() -> None:
    left = {
        "run_id": "run-one",
        "inputs": {"payload": {"q": "old"}, "state": {"x": 1}},
        "retrieval_trace": [{"chunk_id": "c1", "rank": 1}],
        "prompt": {"text": "old prompt", "hash": "a"},
        "output": {"answer": "old"},
        "trust_score_details": {"score": 0.4},
    }
    right = {
        "run_id": "run-two",
        "inputs": {"payload": {"q": "new"}, "state": {"x": 1}},
        "retrieval_trace": [{"chunk_id": "c2", "rank": 1}],
        "prompt": {"text": "new prompt", "hash": "b"},
        "output": {"answer": "new"},
        "trust_score_details": {"score": 0.8},
    }
    first = build_run_diff(left, right)
    second = build_run_diff(left, right)

    assert first == second
    assert first["changed"] is True
    assert [entry["field"] for entry in first["changes"]] == list(RUN_DIFF_FIELD_ORDER)
    assert first["change_count"] == len(RUN_DIFF_FIELD_ORDER)


def test_run_diff_reports_no_changes_when_artifacts_match() -> None:
    artifact = {
        "run_id": "same",
        "inputs": {"payload": {}, "state": {}},
        "retrieval_trace": [],
        "prompt": {"text": "", "hash": ""},
        "output": {"answer": "ok"},
        "trust_score_details": {"score": 1.0},
    }
    payload = build_run_diff(artifact, artifact)
    assert payload["changed"] is False
    assert payload["change_count"] == 0
