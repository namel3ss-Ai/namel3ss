from __future__ import annotations

from namel3ss.runtime.backend.document_highlight import highlights_from_state


def test_phase2_highlights_use_token_positions_fallback_deterministically() -> None:
    state = {
        "index": {
            "chunks": [
                {
                    "chunk_id": "doc-a:0",
                    "document_id": "doc-a",
                    "page_number": 1,
                    "token_positions": [
                        {"index": 0, "token": "Alpha", "start_char": 0, "end_char": 5},
                        {"index": 1, "token": "policy", "start_char": 6, "end_char": 12},
                    ],
                }
            ]
        }
    }
    page_text = "Alpha policy text"
    first = highlights_from_state(state, "doc-a", 1, "doc-a:0", page_text, citation_id="cit.a")
    second = highlights_from_state(state, "doc-a", 1, "doc-a:0", page_text, citation_id="cit.a")

    assert first == second
    assert first == [
        {
            "chunk_id": "doc-a:0",
            "citation_id": "cit.a",
            "color_index": first[0]["color_index"],
            "document_id": "doc-a",
            "end_char": 12,
            "page_number": 1,
            "resolver": "token_positions",
            "start_char": 0,
            "status": "exact",
        }
    ]


def test_phase2_highlights_prefer_bbox_over_span() -> None:
    state = {
        "index": {
            "chunks": [
                {
                    "chunk_id": "doc-b:1",
                    "document_id": "doc-b",
                    "page_number": 2,
                    "bbox": [0.1, 0.2, 0.3, 0.4],
                    "span": {"start_char": 4, "end_char": 10},
                }
            ]
        }
    }
    page_text = "Beta text example"
    rows = highlights_from_state(state, "doc-b", 2, "doc-b:1", page_text, citation_id="cit.b")
    assert len(rows) == 1
    assert rows[0]["resolver"] == "bbox"
    assert rows[0]["status"] == "exact"
    assert rows[0]["bbox"] == [0.1, 0.2, 0.3, 0.4]
