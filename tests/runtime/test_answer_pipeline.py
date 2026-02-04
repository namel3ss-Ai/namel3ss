from __future__ import annotations

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.retrieval.api import run_retrieval
from namel3ss.runtime.answer.api import run_answer
from namel3ss.runtime.ai.provider import AIProvider, AIResponse


class StaticProvider(AIProvider):
    def __init__(self, output: str) -> None:
        self.output = output

    def ask(
        self,
        *,
        model: str,
        system_prompt: str | None,
        user_input: str,
        tools=None,
        memory=None,
        tool_results=None,
    ) -> AIResponse:
        return AIResponse(output=self.output)


def _state_with_chunks(chunks: list[dict]) -> dict:
    ingestion = {entry.get("upload_id"): {"status": "pass"} for entry in chunks if isinstance(entry, dict)}
    return {"ingestion": ingestion, "index": {"chunks": chunks}}


def _sample_chunks() -> list[dict]:
    return [
        {
            "upload_id": "u1",
            "chunk_id": "u1:0",
            "document_id": "doc-1",
            "source_name": "one.txt",
            "page_number": 1,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "text": "The contract was signed on May 1, 2024.",
        },
        {
            "upload_id": "u2",
            "chunk_id": "u2:0",
            "document_id": "doc-2",
            "source_name": "two.txt",
            "page_number": 2,
            "chunk_index": 0,
            "ingestion_phase": "deep",
            "text": "Payment was completed on June 3, 2024.",
        },
    ]


def test_answer_requires_citations() -> None:
    state = _state_with_chunks(_sample_chunks())
    provider = StaticProvider("The contract was signed.")
    with pytest.raises(Namel3ssError) as exc:
        run_answer(
            query="contract",
            state=state,
            project_root=None,
            app_path=None,
            config=AppConfig(),
            provider=provider,
            provider_name="test",
        )
    expected = build_guidance_message(
        what="Answer did not include citations.",
        why="Answers must cite retrieved chunk ids in square brackets.",
        fix="Ensure the model returns citations like [chunk_id].",
        example="The invoice was paid on March 1, 2024. [doc-123:0]",
    )
    assert str(exc.value) == expected
    details = exc.value.details
    assert isinstance(details, dict)
    trace = details.get("answer_trace")
    assert isinstance(trace, dict)
    assert trace.get("status") == "missing_citations"


def test_answer_rejects_unknown_citations() -> None:
    state = _state_with_chunks(_sample_chunks())
    provider = StaticProvider("Signed on May 1, 2024. [unknown]")
    with pytest.raises(Namel3ssError) as exc:
        run_answer(
            query="contract",
            state=state,
            project_root=None,
            app_path=None,
            config=AppConfig(),
            provider=provider,
            provider_name="test",
        )
    expected = build_guidance_message(
        what="Answer cited unknown chunk ids: unknown.",
        why="Citations must reference retrieved chunk ids exactly.",
        fix="Ensure the answer only cites ids from retrieved chunks.",
        example="The invoice was paid on March 1, 2024. [doc-123:0]",
    )
    assert str(exc.value) == expected


def test_prompt_hash_is_deterministic() -> None:
    state = _state_with_chunks(_sample_chunks())
    provider = StaticProvider("Signed on May 1, 2024. [u1:0]")
    first_report, first_meta = run_answer(
        query="contract",
        state=state,
        project_root=None,
        app_path=None,
        config=AppConfig(),
        provider=provider,
        provider_name="test",
    )
    second_report, second_meta = run_answer(
        query="contract",
        state=state,
        project_root=None,
        app_path=None,
        config=AppConfig(),
        provider=StaticProvider("Signed on May 1, 2024. [u1:0]"),
        provider_name="test",
    )
    assert first_meta["prompt_hash"] == second_meta["prompt_hash"]
    assert first_report == second_report


def test_retrieval_results_unchanged_by_answer() -> None:
    state = _state_with_chunks(_sample_chunks())
    before = run_retrieval(query="contract", state=state, project_root=None, app_path=None)
    run_answer(
        query="contract",
        state=state,
        project_root=None,
        app_path=None,
        config=AppConfig(),
        provider=StaticProvider("Signed on May 1, 2024. [u1:0]"),
        provider_name="test",
    )
    after = run_retrieval(query="contract", state=state, project_root=None, app_path=None)
    assert before == after
