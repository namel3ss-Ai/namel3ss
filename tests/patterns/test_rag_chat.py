from __future__ import annotations

import copy

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.patterns.rag_chat import (
    RAG_PATTERNS_CAPABILITY,
    build_rag_chat_pattern,
    validate_rag_chat_pattern,
)


def _walk(nodes: list[dict]) -> list[dict]:
    collected: list[dict] = []
    queue = [entry for entry in nodes if isinstance(entry, dict)]
    while queue:
        node = queue.pop(0)
        collected.append(node)
        for key in ("children", "left", "center", "right", "primary", "secondary"):
            value = node.get(key)
            if isinstance(value, list):
                for child in value:
                    if isinstance(child, dict):
                        queue.append(child)
    return collected


def test_rag_chat_pattern_builds_expected_layout_contract() -> None:
    fragment = build_rag_chat_pattern(capabilities=(RAG_PATTERNS_CAPABILITY,))
    assert fragment["pattern"] == "rag_chat"
    assert fragment["capability"] == RAG_PATTERNS_CAPABILITY

    nodes = _walk(fragment["layout"])
    types = [node["type"] for node in nodes]
    assert "layout.main" in types
    assert "layout.three_pane" in types
    assert "component.chat_thread" in types
    assert "component.citation_panel" in types
    assert "component.document_library" in types
    assert "component.ingestion_progress" in types

    actions = fragment["actions"]
    ordered_actions = sorted(actions.values(), key=lambda action: action["order"])
    assert [action["type"] for action in ordered_actions] == [
        "component.document.select",
        "component.chat.send",
        "component.citation.open",
        "component.ingestion.retry",
    ]



def test_rag_chat_pattern_is_deterministic_across_runs() -> None:
    first = build_rag_chat_pattern(capabilities=(RAG_PATTERNS_CAPABILITY,))
    second = build_rag_chat_pattern(capabilities=(RAG_PATTERNS_CAPABILITY,))
    assert first == second



def test_rag_chat_pattern_requires_capability_outside_studio() -> None:
    with pytest.raises(Namel3ssError) as err:
        build_rag_chat_pattern(capabilities=(), studio_mode=False)
    assert RAG_PATTERNS_CAPABILITY in str(err.value)



def test_rag_chat_validator_rejects_chat_thread_outside_main() -> None:
    fragment = build_rag_chat_pattern(capabilities=(RAG_PATTERNS_CAPABILITY,))
    mutated = copy.deepcopy(fragment)
    main = mutated["layout"][0]
    three_pane = main["children"][0]
    chat = three_pane["center"].pop(0)
    mutated["layout"].append(chat)

    with pytest.raises(Namel3ssError) as err:
        validate_rag_chat_pattern(mutated)
    assert "must be nested under layout.main" in str(err.value)
