from __future__ import annotations

import copy

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.patterns.ingestion_dashboard import (
    build_ingestion_dashboard_pattern,
    validate_ingestion_dashboard_pattern,
)
from namel3ss.ui.patterns.rag_chat import RAG_PATTERNS_CAPABILITY



def test_ingestion_dashboard_pattern_builds_two_pane_contract() -> None:
    fragment = build_ingestion_dashboard_pattern(capabilities=(RAG_PATTERNS_CAPABILITY,))
    assert fragment["pattern"] == "ingestion_dashboard"

    main = fragment["layout"][0]
    assert main["type"] == "layout.main"
    two_pane = main["children"][0]
    assert two_pane["type"] == "layout.two_pane"
    assert two_pane["primary"][0]["type"] == "component.document_library"
    assert two_pane["secondary"][0]["type"] == "component.ingestion_progress"

    ordered_actions = sorted(fragment["actions"].values(), key=lambda action: action["order"])
    assert [action["type"] for action in ordered_actions] == [
        "component.document.select",
        "component.ingestion.retry",
    ]



def test_ingestion_dashboard_pattern_is_deterministic() -> None:
    first = build_ingestion_dashboard_pattern(capabilities=(RAG_PATTERNS_CAPABILITY,))
    second = build_ingestion_dashboard_pattern(capabilities=(RAG_PATTERNS_CAPABILITY,))
    assert first == second



def test_ingestion_dashboard_pattern_requires_capability_outside_studio() -> None:
    with pytest.raises(Namel3ssError) as err:
        build_ingestion_dashboard_pattern(capabilities=(), studio_mode=False)
    assert RAG_PATTERNS_CAPABILITY in str(err.value)



def test_ingestion_dashboard_validator_rejects_missing_secondary_progress() -> None:
    fragment = build_ingestion_dashboard_pattern(capabilities=(RAG_PATTERNS_CAPABILITY,))
    mutated = copy.deepcopy(fragment)
    two_pane = mutated["layout"][0]["children"][0]
    two_pane["secondary"] = []
    with pytest.raises(Namel3ssError) as err:
        validate_ingestion_dashboard_pattern(mutated)
    assert "component.ingestion_progress" in str(err.value)
