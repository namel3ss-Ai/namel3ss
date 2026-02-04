from __future__ import annotations

import hashlib
import re
from decimal import Decimal

from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.policy import PolicyDecision
from namel3ss.retrieval.api import run_retrieval
from namel3ss.runtime.ai.provider import AIProvider
from namel3ss.runtime.ai.providers._shared.parse import normalize_ai_text
from namel3ss.runtime.ai.providers.registry import get_provider
from namel3ss.secrets import collect_secret_values


ANSWER_SYSTEM_PROMPT = "\n".join(
    [
        "You are a precise assistant.",
        "Answer using only the provided sources.",
        "Cite every sentence with [chunk_id] using the exact chunk_id value.",
        "If a sentence uses multiple sources, cite them together like [id1, id2].",
        "Do not cite sources that are not provided.",
    ]
)

_CITATION_RE = re.compile(r"\[([^\[\]]+)\]")


def run_answer(
    *,
    query: str | None,
    state: dict,
    project_root: str | None,
    app_path: str | None,
    limit: int | None = None,
    tier: str | None = None,
    config: AppConfig | None = None,
    provider: AIProvider | None = None,
    provider_name: str | None = None,
    model: str | None = None,
    identity: dict | None = None,
    policy_decision: PolicyDecision | None = None,
    policy_decl: object | None = None,
    capabilities: tuple[str, ...] | list[str] | None = None,
) -> tuple[dict, dict]:
    resolved_config = config or load_config(
        app_path=app_path if isinstance(app_path, str) else None,
        root=project_root if isinstance(project_root, str) else None,
    )
    normalized_query = _normalize_query(query)
    secrets = collect_secret_values(resolved_config)
    retrieval = run_retrieval(
        query=normalized_query,
        limit=limit,
        tier=tier,
        explain=True,
        state=state,
        project_root=project_root,
        app_path=app_path,
        secret_values=secrets,
        identity=identity,
        policy_decision=policy_decision,
        policy_decl=policy_decl,
        config=resolved_config,
        capabilities=capabilities,
    )
    explain_base = _require_explain_bundle(retrieval)
    results = retrieval.get("results") if isinstance(retrieval, dict) else []
    if not isinstance(results, list) or not results:
        explain_bundle = _with_answer_validation(
            explain_base,
            status="no_sources",
            prompt_hash=None,
            citation_count=0,
            unknown_citations=[],
            retrieved_chunk_ids=[],
        )
        raise Namel3ssError(
            _no_sources_message(),
            details=_answer_trace_details([], None, 0, "no_sources", explain_bundle),
        )
    chunk_ids = _chunk_ids(results)
    prompt = build_answer_prompt(normalized_query, results)
    prompt_hash = hash_answer_prompt(prompt)
    resolved_provider_name = _resolve_provider_name(provider_name, resolved_config)
    resolved_model = model or resolved_config.answer.model
    resolved_provider = provider or get_provider(resolved_provider_name, resolved_config)
    response = resolved_provider.ask(
        model=resolved_model,
        system_prompt=ANSWER_SYSTEM_PROMPT,
        user_input=prompt,
        tools=None,
        memory=None,
        tool_results=None,
    )
    raw_output = response.output if hasattr(response, "output") else response
    output_text = normalize_ai_text(raw_output, provider_name=resolved_provider_name, secret_values=secrets)
    citations = _validate_citations(output_text, chunk_ids, prompt_hash, explain_base)
    answer_text = output_text.strip()
    explain_bundle = _with_answer_validation(
        explain_base,
        status="ok",
        prompt_hash=prompt_hash,
        citation_count=len(citations),
        unknown_citations=[],
        retrieved_chunk_ids=chunk_ids,
    )
    report = {
        "answer_text": answer_text,
        "citations": citations,
        "confidence": _confidence_score(len(citations), len(results)),
        "source_count": len(results),
        "explain": explain_bundle,
    }
    meta = {
        "prompt_hash": prompt_hash,
        "chunk_ids": chunk_ids,
        "validation_status": "ok",
        "citation_count": len(citations),
    }
    return report, meta


def build_answer_prompt(query: str, sources: list[dict]) -> str:
    lines: list[str] = []
    lines.append("question:")
    lines.append(str(query or ""))
    lines.append("")
    lines.append("sources:")
    for idx, entry in enumerate(sources, start=1):
        lines.extend(_format_source(entry, idx))
        lines.append("")
    lines.append("answer:")
    return "\n".join(lines).strip()


def hash_answer_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def parse_citations(text: str) -> list[str]:
    if not isinstance(text, str) or not text:
        return []
    citations: list[str] = []
    seen: set[str] = set()
    for match in _CITATION_RE.finditer(text):
        group = match.group(1)
        for raw in group.split(","):
            token = raw.strip()
            if not token:
                continue
            if token in seen:
                continue
            seen.add(token)
            citations.append(token)
    return citations


def _format_source(entry: dict, idx: int) -> list[str]:
    chunk_id = str(entry.get("chunk_id") or "")
    document_id = str(entry.get("document_id") or "")
    source_name = str(entry.get("source_name") or "")
    page_number = entry.get("page_number")
    chunk_index = entry.get("chunk_index")
    ingestion_phase = str(entry.get("ingestion_phase") or "")
    text = str(entry.get("text") or "")
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    lines = [
        f"source {idx}:",
        f"chunk_id: {chunk_id}",
        f"document_id: {document_id}",
        f"source_name: {source_name}",
        f"page_number: {page_number}",
        f"chunk_index: {chunk_index}",
        f"ingestion_phase: {ingestion_phase}",
        "text:",
        normalized_text,
    ]
    return lines


def _validate_citations(
    output_text: str,
    chunk_ids: list[str],
    prompt_hash: str,
    explain_base: dict | None,
) -> list[str]:
    citations = parse_citations(output_text)
    if not citations:
        explain_bundle = _with_answer_validation(
            explain_base,
            status="missing_citations",
            prompt_hash=prompt_hash,
            citation_count=0,
            unknown_citations=[],
            retrieved_chunk_ids=chunk_ids,
        )
        raise Namel3ssError(
            _missing_citations_message(),
            details=_answer_trace_details(chunk_ids, prompt_hash, 0, "missing_citations", explain_bundle),
        )
    allowed = set(chunk_ids)
    unknown = [item for item in citations if item not in allowed]
    if unknown:
        unknown_sorted = sorted(set(unknown))
        explain_bundle = _with_answer_validation(
            explain_base,
            status="unknown_citations",
            prompt_hash=prompt_hash,
            citation_count=len(citations),
            unknown_citations=unknown_sorted,
            retrieved_chunk_ids=chunk_ids,
        )
        raise Namel3ssError(
            _unknown_citations_message(unknown_sorted),
            details=_answer_trace_details(chunk_ids, prompt_hash, len(citations), "unknown_citations", explain_bundle),
        )
    return citations


def _confidence_score(citation_count: int, source_count: int) -> float:
    if source_count <= 0:
        return 0.0
    ratio = Decimal(citation_count) / Decimal(source_count)
    if ratio > Decimal("1"):
        ratio = Decimal("1")
    return float(ratio.quantize(Decimal("0.001")))


def _chunk_ids(results: list[dict]) -> list[str]:
    ids: list[str] = []
    for entry in results:
        if not isinstance(entry, dict):
            continue
        chunk_id = entry.get("chunk_id")
        if chunk_id is None:
            continue
        ids.append(str(chunk_id))
    return ids


def _resolve_provider_name(provider_name: str | None, config: AppConfig) -> str:
    value = provider_name or config.answer.provider
    return str(value or "mock").strip().lower()


def _normalize_query(query: str | None) -> str:
    if query is None:
        return ""
    if not isinstance(query, str):
        raise Namel3ssError(_query_message())
    return query.strip()


def _no_sources_message() -> str:
    return build_guidance_message(
        what="No sources were retrieved for answering.",
        why="Answer generation requires retrieved chunks.",
        fix="Adjust the query or ingest more documents.",
        example='{"query":"invoice"}',
    )


def _query_message() -> str:
    return build_guidance_message(
        what="Answer query must be text.",
        why="Answer generation expects a string query.",
        fix="Provide a text query.",
        example='{"query":"invoice"}',
    )


def _missing_citations_message() -> str:
    return build_guidance_message(
        what="Answer did not include citations.",
        why="Answers must cite retrieved chunk ids in square brackets.",
        fix="Ensure the model returns citations like [chunk_id].",
        example="The invoice was paid on March 1, 2024. [doc-123:0]",
    )


def _unknown_citations_message(unknown: list[str]) -> str:
    unknown_list = ", ".join(unknown) if unknown else "unknown"
    return build_guidance_message(
        what=f"Answer cited unknown chunk ids: {unknown_list}.",
        why="Citations must reference retrieved chunk ids exactly.",
        fix="Ensure the answer only cites ids from retrieved chunks.",
        example="The invoice was paid on March 1, 2024. [doc-123:0]",
    )


def _missing_explain_message() -> str:
    return build_guidance_message(
        what="Answer explain data is missing.",
        why="Explain bundles must be emitted for every answer request.",
        fix="Re-run the request and check retrieval output.",
        example='{"query":"invoice"}',
    )


def _answer_trace_details(
    chunk_ids: list[str],
    prompt_hash: str | None,
    citation_count: int,
    status: str,
    explain: dict | None = None,
) -> dict:
    details = {
        "answer_trace": {
            "chunk_ids": list(chunk_ids),
            "prompt_hash": prompt_hash,
            "citation_count": citation_count,
            "status": status,
        }
    }
    if isinstance(explain, dict):
        details["answer_explain"] = explain
    return details


def _require_explain_bundle(retrieval: dict | None) -> dict:
    if not isinstance(retrieval, dict):
        raise Namel3ssError(_missing_explain_message())
    explain = retrieval.get("explain")
    if not isinstance(explain, dict):
        raise Namel3ssError(_missing_explain_message())
    return dict(explain)


def _with_answer_validation(
    explain: dict | None,
    *,
    status: str,
    prompt_hash: str | None,
    citation_count: int,
    unknown_citations: list[str],
    retrieved_chunk_ids: list[str],
) -> dict | None:
    if not isinstance(explain, dict):
        return None
    payload = dict(explain)
    payload["answer_validation"] = {
        "status": status,
        "citation_count": citation_count,
        "unknown_citations": list(unknown_citations),
        "prompt_hash": prompt_hash,
        "retrieved_chunk_ids": list(retrieved_chunk_ids),
    }
    return payload


__all__ = ["ANSWER_SYSTEM_PROMPT", "build_answer_prompt", "hash_answer_prompt", "parse_citations", "run_answer"]
