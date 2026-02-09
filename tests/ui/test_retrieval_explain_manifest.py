from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.elements.retrieval_explain import inject_retrieval_explain_elements
from tests.conftest import lower_ir_program


def _retrieval_payload() -> dict:
    return {
        "query": "alpha",
        "retrieval_plan": {
            "query": "alpha",
            "tier": {"requested": "auto", "selected": "deep_then_quick"},
            "cutoffs": {"selected_count": 1, "candidate_count": 2},
        },
        "retrieval_trace": [
            {
                "chunk_id": "doc-a:0",
                "document_id": "doc-a",
                "page_number": 1,
                "score": 0.88,
                "rank": 1,
                "reason": "keyword_match",
                "upload_id": "doc-a",
                "quality": "pass",
            }
        ],
        "trust_score_details": {
            "formula_version": "rag_trust@1",
            "score": 0.88,
            "level": "high",
        },
    }


def test_retrieval_explain_manifest_injection_for_standard_page() -> None:
    source = '''
spec is "1.0"

page "home":
  text is "Hello"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    inject_retrieval_explain_elements(manifest, _retrieval_payload())

    elements = manifest["pages"][0]["elements"]
    assert elements[0]["type"] == "retrieval_explain"
    assert elements[0]["query"] == "alpha"
    assert elements[0]["retrieval_trace"][0]["chunk_id"] == "doc-a:0"
    assert elements[0]["trust_score_details"]["score"] == 0.88


def test_retrieval_explain_manifest_injection_for_layout_page() -> None:
    source = '''
spec is "1.0"

page "dashboard":
  layout:
    header:
      text is "Header"
    main:
      text is "Main"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    inject_retrieval_explain_elements(manifest, _retrieval_payload())
    main = manifest["pages"][0]["layout"]["main"]
    assert main[0]["type"] == "retrieval_explain"


def test_retrieval_explain_manifest_injection_is_idempotent() -> None:
    source = '''
spec is "1.0"

page "home":
  text is "Hello"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    payload = _retrieval_payload()
    inject_retrieval_explain_elements(manifest, payload)
    inject_retrieval_explain_elements(manifest, payload)

    elements = manifest["pages"][0]["elements"]
    assert [entry.get("type") for entry in elements].count("retrieval_explain") == 1
