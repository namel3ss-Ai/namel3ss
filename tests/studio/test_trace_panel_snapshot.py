from __future__ import annotations

from pathlib import Path

from namel3ss.studio.panels.retrieval_trace_panel import build_retrieval_trace_panel_payload


def test_trace_panel_payload_is_deterministic_and_sorted() -> None:
    payload = build_retrieval_trace_panel_payload(
        trace_payload={
            "query": "alpha",
            "params": {"semantic_weight": 0.5, "semantic_k": 10, "lexical_k": 10, "final_top_k": 10},
            "filter_tags": ["support", "billing", "support"],
            "final": [
                {"doc_id": "doc-b", "title": "Doc B", "semantic_score": 0.9, "lexical_score": 0.1, "final_score": 0.5},
                {"doc_id": "doc-a", "title": "Doc A", "semantic_score": 0.9, "lexical_score": 0.1, "final_score": 0.5},
            ],
            "semantic": [],
            "lexical": [],
        },
        capabilities=("diagnostics.trace",),
        source_map=[
            {"decl_id": "inc-002-flow-xyz", "file": "modules/b.ai", "line": 5, "col": 1},
            {"decl_id": "inc-001-flow-abc", "file": "modules/a.ai", "line": 3, "col": 1},
        ],
    )
    assert payload["enabled"] is True
    assert payload["available"] is True
    assert payload["trace"]["filter_tags"] == ["billing", "support"]
    assert [row["doc_id"] for row in payload["trace"]["final"]] == ["doc-a", "doc-b"]
    assert [row["decl_id"] for row in payload["source_map"]] == ["inc-001-flow-abc", "inc-002-flow-xyz"]


def test_trace_panel_renderer_wiring_exists() -> None:
    diagnostics_js = Path("src/namel3ss/studio/web/studio/diagnostics.js").read_text(encoding="utf-8")
    trace_js = Path("src/namel3ss/studio/web/ui_renderer_trace.js").read_text(encoding="utf-8")
    assert "retrieval_trace_panel" in diagnostics_js
    assert "renderTracePanelSection" in diagnostics_js
    assert "renderRetrievalTracePanel" in trace_js
    assert "Retrieval Trace" in trace_js
