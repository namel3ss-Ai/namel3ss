from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''flow "send_question":
  return "ok"

page "Ask the Docs":
  layout:
    sidebar_left:
      scope_selector from state.documents active in state.active_docs
    main:
      section "Answer":
        text is "Grounded answer"
        citations from state.answer.citations
        trust_indicator from state.answer.trusted
      chat:
        messages from is state.chat.messages
        citations from state.answer.citations
        trust_indicator from state.answer.trusted
        composer calls flow "send_question"
    drawer_right:
      source_preview from state.preview
'''


STATE = {
    "documents": [
        {"id": "policies", "name": "Policies"},
        {"id": "manuals", "name": "Manuals"},
    ],
    "active_docs": ["policies"],
    "answer": {
        "citations": [
            {"title": "Policy A", "source_id": "doc-a", "snippet": "Source snippet A"},
            {"title": "Policy B", "url": "https://example.com/policy-b"},
        ],
        "trusted": 0.92,
    },
    "preview": {
        "title": "Policy A",
        "source_id": "doc-a",
        "snippet": "Source snippet A",
        "document_id": "doc-a",
        "page_number": 4,
    },
    "chat": {
        "messages": [
            {
                "role": "assistant",
                "content": "Grounded response",
                "trust": 0.9,
                "citations": [{"title": "Policy A", "source_id": "doc-a"}],
            }
        ]
    },
}


def test_rag_manifest_components_and_actions() -> None:
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state=STATE)

    page = manifest["pages"][0]
    elements = list(_walk_page_elements(page))
    by_type: dict[str, list[dict]] = {}
    for element in elements:
        by_type.setdefault(element["type"], []).append(element)

    scope_selector = by_type["scope_selector"][0]
    assert scope_selector["active"] == ["policies"]
    assert scope_selector["options"] == [
        {"id": "policies", "name": "Policies"},
        {"id": "manuals", "name": "Manuals"},
    ]
    action_id = scope_selector["action_id"]
    assert manifest["actions"][action_id]["type"] == "scope_select"
    assert manifest["actions"][action_id]["target_state"] == "state.active_docs"

    trust_indicator = by_type["trust_indicator"][0]
    assert trust_indicator["value"] == 0.92

    citation_chips = by_type["citation_chips"][0]
    assert [entry["index"] for entry in citation_chips["citations"]] == [1, 2]
    assert citation_chips["citations"][0]["source_id"] == "doc-a"

    source_preview = by_type["source_preview"][0]
    assert source_preview["source_id"] == "doc-a"
    assert source_preview["document_id"] == "doc-a"
    assert source_preview["page_number"] == 4

    chat_messages = by_type["messages"][0]["messages"]
    assert chat_messages[0]["trust"] == 0.9
    assert chat_messages[0]["citations"][0]["index"] == 1


def test_rag_manifest_empty_citations_warning() -> None:
    program = lower_ir_program(SOURCE)
    warnings: list = []
    state = dict(STATE)
    state["answer"] = {"citations": [], "trusted": True}
    manifest = build_manifest(program, state=state, warnings=warnings)
    assert manifest["pages"]
    codes = [warning.code for warning in warnings]
    assert "rag.empty_citations_component" in codes


def test_rag_manifest_is_deterministic() -> None:
    program = lower_ir_program(SOURCE)
    first = build_manifest(program, state=STATE)
    second = build_manifest(program, state=STATE)
    assert first == second


def _walk_page_elements(page: dict):
    layout = page.get("layout")
    if isinstance(layout, dict):
        for slot in ("header", "sidebar_left", "main", "drawer_right", "footer"):
            for element in _walk_elements(layout.get(slot, [])):
                yield element
        return
    for element in _walk_elements(page.get("elements", [])):
        yield element


def _walk_elements(elements: list[dict]):
    for element in elements:
        if not isinstance(element, dict):
            continue
        yield element
        children = element.get("children")
        if isinstance(children, list):
            yield from _walk_elements(children)
