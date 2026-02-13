from __future__ import annotations

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.rag.determinism.json_policy import canonical_contract_hash
from namel3ss.rag.evaluation import (
    build_eval_case_model,
    build_golden_query_suite,
    build_regression_report,
    normalize_golden_query_suite,
    raise_on_regression_failure,
    run_eval_suite,
)
from namel3ss.rag.ingestion import run_ingestion_pipeline
from namel3ss.rag.retrieval import run_chat_answer_service
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


def test_golden_query_suite_normalization_is_deterministic() -> None:
    case_alpha = build_eval_case_model(
        query=" alpha policy ",
        expected={
            "expected_chunk_ids": ["chunk.a", "chunk.a", "chunk.b"],
            "expected_doc_ids": ["doc.b", "doc.a"],
            "answer_substrings": ["alpha", "policy", "policy"],
        },
        thresholds={"min_overall_score": 0.9},
        tags=["core", "alpha", "core"],
    )
    case_beta = build_eval_case_model(
        query=" beta policy ",
        expected={"expected_chunk_ids": ["chunk.c"], "min_citation_count": 1},
        thresholds={"min_overall_score": 0.8},
        tags=["core", "beta"],
    )
    first = normalize_golden_query_suite({"name": "core", "cases": [case_beta, case_alpha]})
    second = normalize_golden_query_suite({"name": "core", "cases": [case_alpha, case_beta]})

    assert first == second
    case_ids = [case["case_id"] for case in first["cases"]]
    assert case_ids == sorted(case_ids)
    assert first["suite_id"].startswith("evalsuite_")
    assert first["cases"][0]["expected"]["expected_chunk_ids"] == sorted(
        first["cases"][0]["expected"]["expected_chunk_ids"]
    )


def test_eval_runner_is_deterministic_end_to_end() -> None:
    state: dict = {}
    run_ingestion_pipeline(
        state=state,
        content=b"Alpha policy clause.",
        source_name="policy.txt",
        source_identity="fixtures/eval-policy.txt",
        source_type="upload",
        source_uri="upload://fixtures/eval-policy.txt",
        mime_type="text/plain",
    )
    chunks = list((state.get("index") or {}).get("chunks") or [])
    assert chunks
    first_chunk = dict(chunks[0])
    chunk_id = str(first_chunk.get("chunk_id"))
    doc_id = str(first_chunk.get("document_id") or first_chunk.get("doc_id"))
    provider = StaticProvider(f"Alpha policy clause. [{chunk_id}]")

    suite = build_golden_query_suite(
        name="eval-deterministic",
        cases=[
            build_eval_case_model(
                query="alpha",
                expected={
                    "answer_substrings": ["alpha policy clause"],
                    "expected_chunk_ids": [chunk_id],
                    "expected_doc_ids": [doc_id],
                    "min_citation_count": 1,
                },
                retrieval_config={"top_k": 4, "filters": {"tags": []}, "scope": {"collections": [], "documents": []}},
            )
        ],
    )

    def answer_runner(case: dict[str, object]) -> dict[str, object]:
        return run_chat_answer_service(
            query=str(case.get("query") or ""),
            state=state,
            project_root=None,
            app_path=None,
            provider=provider,
            provider_name="test",
            config=AppConfig(),
            retrieval_config=case.get("retrieval_config"),
        )

    first = run_eval_suite(suite=suite, answer_runner=answer_runner, run_label="baseline")
    second = run_eval_suite(suite=suite, answer_runner=answer_runner, run_label="baseline")

    assert first == second
    assert first["summary"]["pass_rate"] == 1.0
    assert first["summary"]["avg_citation_grounding"] == 1.0
    assert first["summary"]["avg_answer_span_consistency"] == 1.0


def test_answer_span_consistency_detects_invalid_spans() -> None:
    suite = build_golden_query_suite(
        name="eval-invalid-span",
        cases=[
            build_eval_case_model(
                query="alpha",
                expected={"expected_chunk_ids": ["doc-a:0"], "min_citation_count": 1},
            )
        ],
    )

    def answer_runner(_: dict[str, object]) -> dict[str, object]:
        return {
            "answer_text": "alpha answer",
            "citations": [
                {
                    "chunk_id": "doc-a:0",
                    "doc_id": "doc-a",
                    "page_number": 1,
                    "answer_span": {"start_char": 0, "end_char": 100},
                    "preview_target": {"page": 1},
                }
            ],
            "retrieval_results": [
                {
                    "rank": 1,
                    "chunk_id": "doc-a:0",
                    "doc_id": "doc-a",
                    "page_number": 1,
                    "score": 0.8,
                    "rerank_score": 0.8,
                }
            ],
            "retrieval_config": {"top_k": 4},
        }

    report = run_eval_suite(suite=suite, answer_runner=answer_runner)
    case = report["case_results"][0]

    assert case["metrics"]["answer_span_consistency"] == 0.0
    assert any(issue.startswith("invalid_answer_span:") for issue in case["issues"])
    assert case["passed"] is False


def test_regression_gate_blocks_citation_drift() -> None:
    suite = build_golden_query_suite(
        name="eval-regression",
        cases=[
            build_eval_case_model(
                query="alpha",
                expected={
                    "answer_substrings": ["alpha"],
                    "expected_chunk_ids": ["doc-a:0"],
                    "expected_doc_ids": ["doc-a"],
                    "min_citation_count": 1,
                },
            )
        ],
    )

    def good_runner(_: dict[str, object]) -> dict[str, object]:
        return {
            "answer_text": "alpha answer",
            "citations": [
                {
                    "chunk_id": "doc-a:0",
                    "doc_id": "doc-a",
                    "page_number": 1,
                    "answer_span": {"start_char": 0, "end_char": 5},
                    "preview_target": {"page": 1},
                }
            ],
            "retrieval_results": [
                {
                    "rank": 1,
                    "chunk_id": "doc-a:0",
                    "doc_id": "doc-a",
                    "page_number": 1,
                    "score": 0.9,
                    "rerank_score": 0.9,
                }
            ],
            "retrieval_config": {"top_k": 4},
        }

    def bad_runner(_: dict[str, object]) -> dict[str, object]:
        return {
            "answer_text": "alpha answer",
            "citations": [
                {
                    "chunk_id": "doc-z:0",
                    "doc_id": "doc-z",
                    "page_number": 1,
                    "answer_span": {"start_char": 0, "end_char": 5},
                    "preview_target": {"page": 1},
                }
            ],
            "retrieval_results": [
                {
                    "rank": 1,
                    "chunk_id": "doc-a:0",
                    "doc_id": "doc-a",
                    "page_number": 1,
                    "score": 0.9,
                    "rerank_score": 0.9,
                }
            ],
            "retrieval_config": {"top_k": 4},
        }

    baseline = run_eval_suite(suite=suite, answer_runner=good_runner, run_label="baseline")
    current = run_eval_suite(suite=suite, answer_runner=bad_runner, run_label="current")
    regression = build_regression_report(current_run=current, baseline_run=baseline)

    assert regression["passed"] is False
    failed_gate_ids = [gate["gate_id"] for gate in regression["gates"] if not gate["passed"]]
    assert "avg_citation_grounding.drop_max" in failed_gate_ids
    with pytest.raises(RuntimeError):
        raise_on_regression_failure(regression)


def test_eval_and_regression_reports_are_snapshot_stable() -> None:
    suite = build_golden_query_suite(
        name="eval-snapshot",
        cases=[
            build_eval_case_model(
                query="alpha",
                expected={"answer_substrings": ["alpha"], "expected_chunk_ids": ["doc-a:0"], "min_citation_count": 1},
            )
        ],
    )

    def answer_runner(_: dict[str, object]) -> dict[str, object]:
        return {
            "answer_text": "alpha answer",
            "citations": [
                {
                    "chunk_id": "doc-a:0",
                    "doc_id": "doc-a",
                    "page_number": 1,
                    "answer_span": {"start_char": 0, "end_char": 5},
                    "preview_target": {"page": 1},
                }
            ],
            "retrieval_results": [
                {
                    "rank": 1,
                    "chunk_id": "doc-a:0",
                    "doc_id": "doc-a",
                    "page_number": 1,
                    "score": 0.9,
                    "rerank_score": 0.9,
                }
            ],
            "retrieval_config": {"top_k": 4},
        }

    eval_first = run_eval_suite(suite=suite, answer_runner=answer_runner)
    eval_second = run_eval_suite(suite=suite, answer_runner=answer_runner)
    regression_first = build_regression_report(current_run=eval_first, baseline_run=eval_first)
    regression_second = build_regression_report(current_run=eval_second, baseline_run=eval_second)

    assert eval_first == eval_second
    assert regression_first == regression_second
    assert canonical_contract_hash(eval_first) == canonical_contract_hash(eval_second)
    assert canonical_contract_hash(regression_first) == canonical_contract_hash(regression_second)


__all__ = []
