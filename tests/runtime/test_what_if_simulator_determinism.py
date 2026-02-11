from __future__ import annotations

from namel3ss.runtime.retrieval.what_if_simulator import simulate_ranking_from_trace


TRACE = {
    "query": "alpha",
    "params": {
        "semantic_weight": 0.6,
        "semantic_k": 10,
        "lexical_k": 10,
        "final_top_k": 10,
    },
    "final": [
        {
            "doc_id": "doc-b",
            "title": "Doc B",
            "semantic_score": 0.8,
            "lexical_score": 0.2,
            "final_score": 0.56,
            "matched_tags": ["support"],
        },
        {
            "doc_id": "doc-a",
            "title": "Doc A",
            "semantic_score": 0.8,
            "lexical_score": 0.2,
            "final_score": 0.56,
            "matched_tags": ["billing"],
        },
        {
            "doc_id": "doc-c",
            "title": "Doc C",
            "semantic_score": 0.3,
            "lexical_score": 0.9,
            "final_score": 0.54,
            "matched_tags": ["ops"],
        },
    ],
}


def test_what_if_simulation_is_deterministic() -> None:
    params = {"semantic_weight": 0.5, "semantic_k": 2, "lexical_k": 2, "final_top_k": 2}
    first = simulate_ranking_from_trace(TRACE, params=params)
    second = simulate_ranking_from_trace(TRACE, params=params)
    assert first == second
    assert [entry["doc_id"] for entry in first["final"]] == ["doc-c", "doc-a"]
