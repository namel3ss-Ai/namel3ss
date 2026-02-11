from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.elements.retrieval_explain import inject_retrieval_explain_elements
from tests.conftest import lower_ir_program


def _retrieval_payload() -> dict:
    return {
        "query": "invoice policy",
        "retrieval_tuning": {
            "semantic_k": 5,
            "lexical_k": 5,
            "final_top_k": 3,
            "semantic_weight": 0.5,
            "explicit": True,
        },
        "retrieval_plan": {
            "tier": {"requested": "auto", "selected": "deep"},
            "cutoffs": {"selected_count": 1, "candidate_count": 2},
        },
        "retrieval_trace": [
            {
                "chunk_id": "doc-a:0",
                "document_id": "doc-a",
                "page_number": 1,
                "score": 0.91,
                "rank": 1,
                "reason": "keyword_match",
            }
        ],
        "trust_score_details": {"formula_version": "rag_trust@1", "score": 0.91, "level": "high"},
    }


def _first_retrieval_element(manifest: dict) -> dict:
    page = manifest["pages"][0]
    if isinstance(page.get("elements"), list):
        return next(entry for entry in page["elements"] if entry.get("type") == "retrieval_explain")
    return next(entry for entry in page["layout"]["main"] if entry.get("type") == "retrieval_explain")


def _behavior_snapshot(manifest: dict) -> dict:
    element = _first_retrieval_element(manifest)
    trace = tuple(
        (entry.get("chunk_id"), entry.get("rank"), entry.get("reason"))
        for entry in element.get("retrieval_trace", [])
        if isinstance(entry, dict)
    )
    controls = tuple(
        (entry.get("flow"), bool(entry.get("enabled")))
        for entry in element.get("retrieval_controls", {}).get("items", [])
        if isinstance(entry, dict)
    )
    return {
        "query": element.get("query"),
        "trace": trace,
        "trust_level": element.get("trust_score_details", {}).get("level"),
        "controls": controls,
    }


def test_retrieval_snapshot_assertions_do_not_depend_on_layout_ids() -> None:
    source_a = '''
spec is "1.0"

page "home":
  text is "A"
'''.lstrip()
    source_b = '''
spec is "1.0"

page "dashboard":
  layout:
    header:
      text is "Header"
    main:
      text is "Body"
'''.lstrip()
    payload = _retrieval_payload()

    manifest_a = build_manifest(lower_ir_program(source_a), state={}, store=None)
    manifest_b = build_manifest(lower_ir_program(source_b), state={}, store=None)
    inject_retrieval_explain_elements(manifest_a, payload)
    inject_retrieval_explain_elements(manifest_b, payload)

    element_a = _first_retrieval_element(manifest_a)
    element_b = _first_retrieval_element(manifest_b)
    assert element_a["element_id"] != element_b["element_id"]

    assert _behavior_snapshot(manifest_a) == _behavior_snapshot(manifest_b)
