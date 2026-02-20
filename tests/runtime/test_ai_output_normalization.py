from __future__ import annotations

from namel3ss.runtime.ai.providers._shared.parse import normalize_ai_text


def test_normalize_ai_text_keeps_standard_mock_text() -> None:
    value = "[gpt-4.1] You are a helper. :: Hello | mem:st=0"
    assert normalize_ai_text(value, provider_name="mock") == value


def test_normalize_ai_text_rewrites_mock_structured_query_context_echo() -> None:
    value = '[gpt-4o-mini] {"context":"Document summary.","query":"what is this pdf about?"} | mem:st=0'
    assert normalize_ai_text(value, provider_name="mock") == "Document summary."


def test_normalize_ai_text_rewrites_mock_structured_query_context_echo_with_empty_context() -> None:
    value = '[gpt-4o-mini] {"context":"","query":"what is this pdf about?"} | mem:st=0'
    assert normalize_ai_text(value, provider_name="mock") == ""


def test_normalize_ai_text_does_not_rewrite_non_mock_provider() -> None:
    value = '[gpt-4o-mini] {"context":"Document summary.","query":"what is this pdf about?"} | mem:st=0'
    assert normalize_ai_text(value, provider_name="openai") == value
