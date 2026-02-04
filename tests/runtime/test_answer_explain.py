from __future__ import annotations

import json

from namel3ss.config.model import AppConfig
from namel3ss.retrieval.api import run_retrieval
from namel3ss.runtime.answer.api import build_answer_prompt, hash_answer_prompt, run_answer
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


def _state_with_candidates() -> dict:
    return {
        "ingestion": {
            "u1": {"status": "pass"},
            "u2": {"status": "pass"},
            "u3": {"status": "block"},
        },
        "index": {
            "chunks": [
                {
                    "upload_id": "u1",
                    "chunk_id": "u1:0",
                    "document_id": "u1",
                    "source_name": "one.txt",
                    "page_number": 1,
                    "chunk_index": 0,
                    "ingestion_phase": "deep",
                    "text": "alpha policy",
                    "keywords": ["alpha"],
                },
                {
                    "upload_id": "u2",
                    "chunk_id": "u2:0",
                    "document_id": "u2",
                    "source_name": "two.txt",
                    "page_number": 2,
                    "chunk_index": 0,
                    "ingestion_phase": "quick",
                    "text": "alpha beta",
                    "keywords": ["alpha", "beta"],
                },
                {
                    "upload_id": "u2",
                    "chunk_id": "u2:1",
                    "document_id": "u2",
                    "source_name": "two.txt",
                    "page_number": 3,
                    "chunk_index": 1,
                    "ingestion_phase": "quick",
                    "text": "gamma",
                    "keywords": ["gamma"],
                },
                {
                    "upload_id": "u3",
                    "chunk_id": "u3:0",
                    "document_id": "u3",
                    "source_name": "blocked.txt",
                    "page_number": 4,
                    "chunk_index": 0,
                    "ingestion_phase": "deep",
                    "text": "alpha blocked",
                    "keywords": ["alpha"],
                },
            ]
        },
    }


def test_answer_explain_bundle_is_deterministic() -> None:
    state = _state_with_candidates()
    provider = StaticProvider("Alpha answer. [u1:0]")
    report, meta = run_answer(
        query="alpha",
        state=state,
        project_root=None,
        app_path=None,
        limit=1,
        config=AppConfig(),
        provider=provider,
        provider_name="test",
    )
    explain = report.get("explain")
    assert isinstance(explain, dict)

    retrieval = run_retrieval(query="alpha", state=state, project_root=None, app_path=None, limit=1)
    prompt = build_answer_prompt("alpha", retrieval.get("results") or [])
    prompt_hash = hash_answer_prompt(prompt)

    expected = {
        "query": "alpha",
        "retrieval_mode": "auto",
        "candidate_count": 4,
        "candidates": [
            {
                "chunk_id": "u1:0",
                "ingestion_phase": "deep",
                "keyword_overlap": 1,
                "page_number": 1,
                "chunk_index": 0,
                "decision": "selected",
                "reason": "top_k",
            },
            {
                "chunk_id": "u2:0",
                "ingestion_phase": "quick",
                "keyword_overlap": 1,
                "page_number": 2,
                "chunk_index": 0,
                "decision": "excluded",
                "reason": "lower_rank",
            },
            {
                "chunk_id": "u2:1",
                "ingestion_phase": "quick",
                "keyword_overlap": 0,
                "page_number": 3,
                "chunk_index": 1,
                "decision": "excluded",
                "reason": "filtered",
            },
            {
                "chunk_id": "u3:0",
                "ingestion_phase": "deep",
                "keyword_overlap": 1,
                "page_number": 4,
                "chunk_index": 0,
                "decision": "excluded",
                "reason": "blocked",
            },
        ],
        "final_selection": ["u1:0"],
        "ordering": "ingestion_phase, keyword_overlap, page_number, chunk_index",
        "answer_validation": {
            "status": "ok",
            "citation_count": 1,
            "unknown_citations": [],
            "prompt_hash": prompt_hash,
            "retrieved_chunk_ids": ["u1:0"],
        },
    }
    assert explain == expected
    assert report.get("answer_text") == "Alpha answer. [u1:0]"
    assert meta.get("prompt_hash") == prompt_hash


def test_explain_ordering_matches_retrieval() -> None:
    state = _state_with_candidates()
    provider = StaticProvider("Alpha answer. [u1:0]")
    report, _ = run_answer(
        query="alpha",
        state=state,
        project_root=None,
        app_path=None,
        limit=1,
        config=AppConfig(),
        provider=provider,
        provider_name="test",
    )
    explain = report.get("explain") or {}
    retrieval = run_retrieval(query="alpha", state=state, project_root=None, app_path=None, limit=1)
    result_ids = [entry.get("chunk_id") for entry in retrieval.get("results") or []]
    assert explain.get("final_selection") == result_ids


def test_explain_has_no_side_effects() -> None:
    state = _state_with_candidates()
    before = json.loads(json.dumps(state))
    provider = StaticProvider("Alpha answer. [u1:0]")
    run_answer(
        query="alpha",
        state=state,
        project_root=None,
        app_path=None,
        limit=1,
        config=AppConfig(),
        provider=provider,
        provider_name="test",
    )
    assert state == before
