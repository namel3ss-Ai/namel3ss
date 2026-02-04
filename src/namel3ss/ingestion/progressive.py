from __future__ import annotations

from typing import Callable

from namel3ss.ingestion.chunk import chunk_pages
from namel3ss.ingestion.store import store_report, update_index
from namel3ss.secrets import collect_secret_values

PHASE_QUICK = "quick"
PHASE_DEEP = "deep"

DEEP_SCAN_JOB_NAME = "ingestion.deep_scan"

QUICK_SCAN_MAX_CHARS = 2000
QUICK_SCAN_OVERLAP = 200
DEEP_SCAN_MAX_CHARS = 800
DEEP_SCAN_OVERLAP = 100


def chunk_with_phase(
    pages: list[str],
    *,
    document_id: str,
    source_name: str,
    phase: str | None,
    max_chars: int,
    overlap: int,
) -> list[dict]:
    chunks = chunk_pages(pages, max_chars=max_chars, overlap=overlap)
    for chunk in chunks:
        chunk["document_id"] = document_id
        chunk["source_name"] = source_name
        if phase:
            chunk["ingestion_phase"] = phase
    return chunks


def initial_phase_status(status: str) -> dict:
    quick_status = "complete"
    deep_status = "pending"
    if status == "block":
        deep_status = "failed"
    return {
        "quick": phase_summary(quick_status, [], result_status=status),
        "deep": {"status": deep_status},
    }


def phase_summary(status: str, chunks: list[dict], *, result_status: str | None = None) -> dict:
    summary = {
        "status": status,
        "chunk_count": len(chunks),
        "chunk_chars": sum(int(chunk.get("chars") or 0) for chunk in chunks if isinstance(chunk, dict)),
    }
    if result_status:
        summary["result_status"] = result_status
    return summary


def quick_progress_events(upload_id: str, source_name: str, status: str) -> list[dict]:
    return [
        {"title": "reading document", "phase": PHASE_QUICK, "upload_id": upload_id, "source_name": source_name},
        {"title": "extracting text", "phase": PHASE_QUICK, "upload_id": upload_id, "source_name": source_name},
        {
            "title": "quick scan complete",
            "phase": PHASE_QUICK,
            "upload_id": upload_id,
            "source_name": source_name,
            "status": status,
        },
    ]


def deep_scan_job_handler(prepare_ingestion: Callable[..., object]) -> Callable[[object, object], dict]:
    def _handler(ctx, payload: object) -> dict:
        data = payload if isinstance(payload, dict) else {}
        upload_id = str(data.get("upload_id") or "").strip()
        if not upload_id:
            return {"status": "failed", "reason": "missing_upload_id"}
        report = _read_report(ctx.state, upload_id)
        source_name = _report_source_name(report)
        phases = report.get("phases")
        if not isinstance(phases, dict):
            report["phases"] = {}
        status = "complete"
        try:
            if report.get("status") == "block":
                status = "failed"
                _mark_deep_phase(report, status="failed", reason="blocked")
                _append_progress(ctx, report, _deep_progress_events(upload_id, source_name, "failed"))
                store_report(ctx.state, upload_id=upload_id, report=report)
                return {"status": "blocked"}
            secret_values = collect_secret_values(getattr(ctx, "config", None))
            prepared = prepare_ingestion(
                upload_id=upload_id,
                mode=data.get("mode"),
                project_root=getattr(ctx, "project_root", None),
                app_path=getattr(ctx, "app_path", None),
                secret_values=secret_values,
            )
            deep_chunks = chunk_with_phase(
                prepared.sanitized_pages,
                document_id=upload_id,
                source_name=prepared.source_name,
                phase=PHASE_DEEP,
                max_chars=DEEP_SCAN_MAX_CHARS,
                overlap=DEEP_SCAN_OVERLAP,
            )
            update_index(
                ctx.state,
                upload_id=upload_id,
                chunks=deep_chunks,
                low_quality=report.get("status") == "warn",
            )
            report["phases"]["deep"] = phase_summary("complete", deep_chunks)
        except Exception as exc:
            status = "failed"
            _mark_deep_phase(report, status="failed", reason=str(exc))
        _append_progress(ctx, report, _deep_progress_events(upload_id, source_name, status))
        store_report(ctx.state, upload_id=upload_id, report=report)
        return {"status": status}

    return _handler


def _deep_progress_events(upload_id: str, source_name: str, status: str) -> list[dict]:
    return [
        {"title": "deep scan started", "phase": PHASE_DEEP, "upload_id": upload_id, "source_name": source_name},
        {"title": "refining chunks", "phase": PHASE_DEEP, "upload_id": upload_id, "source_name": source_name},
        {
            "title": "deep scan complete",
            "phase": PHASE_DEEP,
            "upload_id": upload_id,
            "source_name": source_name,
            "status": status,
        },
    ]


def _read_report(state: dict, upload_id: str) -> dict:
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, dict):
        return {"upload_id": upload_id, "phases": {}}
    report = ingestion.get(upload_id)
    if not isinstance(report, dict):
        return {"upload_id": upload_id, "phases": {}}
    return report


def _report_source_name(report: dict) -> str:
    provenance = report.get("provenance")
    if isinstance(provenance, dict):
        source_name = provenance.get("source_name")
        if isinstance(source_name, str) and source_name.strip():
            return source_name.strip()
    return "upload"


def _append_progress(ctx, report: dict, events: list[dict]) -> None:
    existing = report.get("progress")
    progress = list(existing) if isinstance(existing, list) else []
    progress.extend(events)
    report["progress"] = progress
    traces = getattr(ctx, "traces", None)
    if isinstance(traces, list):
        traces.extend(_progress_traces(events))


def _progress_traces(events: list[dict]) -> list[dict]:
    traces: list[dict] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        trace = {
            "type": "ingestion_progress",
            "title": event.get("title"),
            "upload_id": event.get("upload_id"),
            "source_name": event.get("source_name"),
            "ingestion_phase": event.get("phase"),
        }
        if "status" in event:
            trace["status"] = event.get("status")
        traces.append(trace)
    return traces


def _mark_deep_phase(report: dict, *, status: str, reason: str | None = None) -> None:
    phases = report.get("phases")
    if not isinstance(phases, dict):
        phases = {}
    entry = {"status": status}
    if reason:
        entry["reason"] = reason
    phases["deep"] = entry
    report["phases"] = phases


__all__ = [
    "DEEP_SCAN_JOB_NAME",
    "DEEP_SCAN_MAX_CHARS",
    "DEEP_SCAN_OVERLAP",
    "PHASE_DEEP",
    "PHASE_QUICK",
    "QUICK_SCAN_MAX_CHARS",
    "QUICK_SCAN_OVERLAP",
    "chunk_with_phase",
    "deep_scan_job_handler",
    "initial_phase_status",
    "phase_summary",
    "quick_progress_events",
]
