from __future__ import annotations

from types import SimpleNamespace

from namel3ss.errors.base import Namel3ssError
from namel3ss.ingestion.api import run_ingestion_progressive
from namel3ss.ingestion.api import _resolve_metadata  # internal helper
from namel3ss.pipelines.model import (
    PipelineRunResult,
    PipelineStepResult,
    pipeline_step_id,
    step_checksum,
    validate_step_summary,
)
from namel3ss.pipelines.registry import pipeline_definitions
from namel3ss.retrieval.api import run_retrieval
from namel3ss.secrets import collect_secret_values


def run_pipeline(ctx, *, name: str, payload: dict) -> PipelineRunResult:
    definition = pipeline_definitions().get(name)
    if definition is None:
        raise Namel3ssError(f'Unknown pipeline "{name}".')
    if name == "ingestion":
        return _run_ingestion(ctx, definition, payload)
    if name == "retrieval":
        return _run_retrieval(ctx, definition, payload)
    raise Namel3ssError(f'Unknown pipeline "{name}".')


def _run_ingestion(ctx, definition, payload: dict) -> PipelineRunResult:
    steps: list[PipelineStepResult] = []
    upload_id = str(payload.get("upload_id") or "")
    meta_ctx = SimpleNamespace(project_root=ctx.project_root, app_path=ctx.app_path)
    metadata = _resolve_metadata(meta_ctx, upload_id)
    accept_summary = {
        "upload_id": upload_id,
        "content_type": str(metadata.get("content_type") or ""),
        "size": int(metadata.get("size") or 0),
    }
    steps.append(_build_step(definition, 1, accept_summary, status="ok"))

    secret_list = collect_secret_values(ctx.config)
    result = run_ingestion_progressive(
        upload_id=upload_id,
        mode=str(payload.get("mode")) if isinstance(payload.get("mode"), str) else None,
        state=ctx.state,
        project_root=ctx.project_root,
        app_path=ctx.app_path,
        secret_values=secret_list,
        job_ctx=ctx,
    )
    report = result.get("report") if isinstance(result, dict) else None
    if not isinstance(report, dict):
        raise Namel3ssError("Ingestion report is missing.")
    detected = report.get("detected") or {}
    detected_type = str(detected.get("type") or "")
    signals = report.get("signals") or {}
    text_chars = int(signals.get("text_chars") or 0)
    extract_summary = {
        "method_used": str(report.get("method_used") or ""),
        "detected_type": detected_type,
        "text_chars": text_chars,
    }
    steps.append(_build_step(definition, 2, extract_summary, status="ok"))

    quality_summary = {
        "status": str(report.get("status") or ""),
        "reasons": list(report.get("reasons") or []),
    }
    steps.append(_build_step(definition, 3, quality_summary, status="ok"))

    chunks = result.get("chunks") if isinstance(result, dict) else []
    if not isinstance(chunks, list):
        chunks = []
    chunk_chars = sum(int(chunk.get("chars") or 0) for chunk in chunks if isinstance(chunk, dict))
    chunk_summary = {
        "chunk_count": len(chunks),
        "chunk_chars": chunk_chars,
    }
    chunk_status = "skipped" if report.get("status") == "block" else "ok"
    steps.append(_build_step(definition, 4, chunk_summary, status=chunk_status))

    indexed_chunks = _count_index_entries(ctx.state, upload_id)
    index_summary = {
        "indexed_chunks": indexed_chunks,
        "low_quality": bool(report.get("status") == "warn"),
    }
    index_status = "skipped" if report.get("status") == "block" else "ok"
    steps.append(_build_step(definition, 5, index_summary, status=index_status))

    report_summary = {
        "report_status": str(report.get("status") or ""),
        "report_checksum": step_checksum(report),
    }
    steps.append(_build_step(definition, 6, report_summary, status="ok"))

    output = {
        "report": report,
        "ingestion": ctx.state.get("ingestion"),
        "index": ctx.state.get("index"),
    }
    return PipelineRunResult(output=output, steps=steps, status="ok")


def _run_retrieval(ctx, definition, payload: dict) -> PipelineRunResult:
    steps: list[PipelineStepResult] = []
    query = payload.get("query")
    limit = payload.get("limit")
    accept_summary = {
        "query": str(query or ""),
        "limit": limit,
    }
    steps.append(_build_step(definition, 1, accept_summary, status="ok"))

    result = run_retrieval(
        query=query,
        limit=limit,
        tier=payload.get("tier"),
        state=_retrieval_state_view(ctx.state, payload),
        project_root=ctx.project_root,
        app_path=ctx.app_path,
        secret_values=collect_secret_values(ctx.config),
        identity=ctx.identity,
        policy_decl=getattr(ctx, "policy", None),
    )
    excluded_blocked = int(result.get("excluded_blocked") or 0) if isinstance(result, dict) else 0
    excluded_warn = int(result.get("excluded_warn") or 0) if isinstance(result, dict) else 0
    warn_allowed = bool(result.get("warn_allowed")) if isinstance(result, dict) else False
    select_summary = {
        "excluded_blocked": excluded_blocked,
        "excluded_warn": excluded_warn,
        "warn_allowed": warn_allowed,
    }
    steps.append(_build_step(definition, 2, select_summary, status="ok"))

    results = result.get("results") if isinstance(result, dict) else []
    if not isinstance(results, list):
        results = []
    retrieve_summary = {"matched_results": len(results)}
    steps.append(_build_step(definition, 3, retrieve_summary, status="ok"))

    rank_summary = {
        "ordering": "phase_keyword_overlap_page_chunk",
        "tie_break": "index_order",
    }
    steps.append(_build_step(definition, 4, rank_summary, status="ok"))

    schema_keys = _result_schema_keys(results)
    shape_summary = {"result_count": len(results), "schema_keys": schema_keys}
    steps.append(_build_step(definition, 5, shape_summary, status="ok"))

    report_summary = {
        "preferred_quality": str(result.get("preferred_quality") or "pass"),
        "included_warn": bool(result.get("included_warn")) if isinstance(result, dict) else False,
    }
    steps.append(_build_step(definition, 6, report_summary, status="ok"))

    return PipelineRunResult(output={"report": result}, steps=steps, status="ok")


def _retrieval_state_view(state: dict, payload: dict) -> dict:
    if "ingestion" not in payload and "index" not in payload:
        return state
    view = dict(state)
    if "ingestion" in payload:
        view["ingestion"] = payload.get("ingestion")
    if "index" in payload:
        view["index"] = payload.get("index")
    return view


def _count_index_entries(state: dict, upload_id: str) -> int:
    index = state.get("index")
    if not isinstance(index, dict):
        return 0
    chunks = index.get("chunks")
    if not isinstance(chunks, list):
        return 0
    return sum(1 for entry in chunks if isinstance(entry, dict) and entry.get("upload_id") == upload_id)


def _result_schema_keys(results: list[dict]) -> list[str]:
    keys: set[str] = set()
    for entry in results:
        if isinstance(entry, dict):
            keys.update(str(key) for key in entry.keys())
    return sorted(keys)


def _build_step(definition, ordinal: int, summary: dict, *, status: str) -> PipelineStepResult:
    step = definition.steps[ordinal - 1]
    validate_step_summary(step, summary)
    checksum = step_checksum(summary)
    return PipelineStepResult(
        step_id=pipeline_step_id(definition.name, step.kind, ordinal),
        kind=step.kind,
        status=status,
        summary=summary,
        checksum=checksum,
        ordinal=ordinal,
    )


__all__ = ["run_pipeline"]
