from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ingestion.policy import ACTION_RETRIEVAL_INCLUDE_WARN, PolicyDecision
from namel3ss.retrieval.api import run_retrieval
from namel3ss.retrieval.embedding_plan import EmbeddingPlan
from namel3ss.runtime.retrieval.set_semantic_weight import set_semantic_weight
from tests.conftest import lower_ir_program, run_flow


def _allow_warn() -> PolicyDecision:
    return PolicyDecision(
        action=ACTION_RETRIEVAL_INCLUDE_WARN,
        allowed=True,
        reason="test",
        required_permissions=(),
        source="test",
    )


def _state(chunks: list[dict], *, tuning: dict | None = None) -> dict:
    ingestion = {}
    for chunk in chunks:
        upload_id = chunk.get("upload_id")
        if isinstance(upload_id, str):
            ingestion[upload_id] = {"status": "pass"}
    state = {"ingestion": ingestion, "index": {"chunks": chunks}}
    if tuning is not None:
        state["retrieval"] = {"tuning": tuning}
    return state


def _chunks() -> list[dict]:
    return [
        {
            "upload_id": "u1",
            "chunk_id": "u1:0",
            "document_id": "u1",
            "source_name": "one.txt",
            "page_number": 1,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "keywords": ["alpha", "beta"],
            "text": "alpha beta deterministic",
        },
        {
            "upload_id": "u2",
            "chunk_id": "u2:0",
            "document_id": "u2",
            "source_name": "two.txt",
            "page_number": 1,
            "chunk_index": 1,
            "ingestion_phase": "deep",
            "keywords": ["alpha"],
            "text": "alpha semantic",
        },
        {
            "upload_id": "u3",
            "chunk_id": "u3:0",
            "document_id": "u3",
            "source_name": "three.txt",
            "page_number": 2,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "keywords": ["gamma"],
            "text": "semantic only evidence",
        },
    ]


def _patch_embedding_plan(monkeypatch, scores: dict[str, float]) -> None:
    candidates = [
        {"chunk_id": chunk_id, "score": score}
        for chunk_id, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    ]
    plan = EmbeddingPlan(
        enabled=True,
        model_id="test-model",
        candidate_ids=frozenset(scores.keys()),
        scores=dict(scores),
        candidates=candidates,
    )
    monkeypatch.setattr("namel3ss.retrieval.api.build_embedding_plan", lambda *args, **kwargs: plan)


def test_runtime_retrieval_tuning_builtins_update_state() -> None:
    source = '''
spec is "1.0"

flow "demo":
  let _a is set_semantic_k(2)
  let _b is set_lexical_k(3)
  let _d is set_semantic_weight(0.75)
  let _c is set_final_top_k(1)
  return "ok"
'''.lstrip()
    result = run_flow(source)
    assert result.state["retrieval"]["tuning"] == {
        "semantic_k": 2,
        "lexical_k": 3,
        "final_top_k": 1,
        "semantic_weight": 0.75,
    }


def test_compile_time_retrieval_tuning_validation_rejects_invalid_literals() -> None:
    source = '''
spec is "1.0"

flow "demo":
  let _value is set_semantic_k(-1)
  return "ok"
'''.lstrip()
    with pytest.raises(Namel3ssError, match="InvalidRetrievalParameterError"):
        lower_ir_program(source)


def test_compile_time_retrieval_tuning_validation_rejects_invalid_order() -> None:
    source = '''
spec is "1.0"

flow "demo":
  let _value is set_final_top_k(2)
  let _semantic is set_semantic_k(4)
  let _lexical is set_lexical_k(4)
  return "ok"
'''.lstrip()
    with pytest.raises(Namel3ssError, match="InvalidRetrievalParameterError"):
        lower_ir_program(source)


def test_runtime_retrieval_tuning_weight_bounds_raise_value_error() -> None:
    with pytest.raises(ValueError, match="weight in \\[0, 1\\]"):
        set_semantic_weight({}, 1.5)


def test_retrieval_tuning_adjusts_weight_and_top_k(monkeypatch) -> None:
    _patch_embedding_plan(monkeypatch, {"u1:0": 0.1, "u2:0": 0.95, "u3:0": 0.9})
    state = _state(
        _chunks(),
        tuning={
            "semantic_k": 2,
            "lexical_k": 2,
            "final_top_k": 2,
            "semantic_weight": 1.0,
        },
    )
    first = run_retrieval(
        query="alpha beta",
        state=state,
        project_root=None,
        app_path=None,
        policy_decision=_allow_warn(),
    )
    second = run_retrieval(
        query="alpha beta",
        state=state,
        project_root=None,
        app_path=None,
        policy_decision=_allow_warn(),
    )
    assert first == second
    assert [entry["chunk_id"] for entry in first["results"]] == ["u2:0", "u3:0"]
    assert first["retrieval_tuning"]["explicit"] is True
    assert first["retrieval_tuning"]["semantic_weight"] == 1.0
    assert first["retrieval_plan"]["tuning"]["semantic_weight"] == 1.0


def test_retrieval_tuning_handles_k_edge_cases(monkeypatch) -> None:
    _patch_embedding_plan(monkeypatch, {"u1:0": 0.1, "u2:0": 0.95, "u3:0": 0.9})
    zero_state = _state(
        _chunks(),
        tuning={
            "semantic_k": 0,
            "lexical_k": 0,
            "final_top_k": 5,
            "semantic_weight": 0.5,
        },
    )
    zero = run_retrieval(
        query="alpha beta",
        state=zero_state,
        project_root=None,
        app_path=None,
        policy_decision=_allow_warn(),
    )
    assert zero["results"] == []

    large_state = _state(
        _chunks(),
        tuning={
            "semantic_k": 100,
            "lexical_k": 100,
            "final_top_k": 100,
            "semantic_weight": 0.5,
        },
    )
    large = run_retrieval(
        query="alpha beta",
        state=large_state,
        project_root=None,
        app_path=None,
        policy_decision=_allow_warn(),
    )
    assert len(large["results"]) == 3
