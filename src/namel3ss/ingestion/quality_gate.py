from __future__ import annotations

import os
from typing import Iterable

from namel3ss.ingestion.chunk_plan import plan_chunks
from namel3ss.ingestion.gate_cache import gate_root, read_cache_entry, write_cache_entry, write_quarantine_entry
from namel3ss.ingestion.gate_contract import (
    EVIDENCE_EXCERPT_LIMIT,
    PROBE_REASON_ORDER,
    QUALITY_REASON_ORDER,
    gate_runtime_signature,
)
from namel3ss.ingestion.gate_probe import probe_content
from namel3ss.ingestion.hash import hash_bytes
from namel3ss.ingestion.normalize import preview_text


ENV_CHUNK_PLAN = "N3_INGESTION_CHUNK_PLAN"


def evaluate_gate(
    *,
    content: bytes,
    metadata: dict,
    detected: dict,
    normalized_text: str | None,
    quality_status: str,
    quality_reasons: Iterable[str],
    project_root: str | None,
    app_path: str | None,
    secret_values: list[str] | None,
    probe: dict | None = None,
    enable_chunk_plan: bool | None = None,
) -> dict:
    probe_result = probe or probe_content(content, metadata=metadata, detected=detected)
    merged_reasons = _merge_reasons(probe_result, quality_reasons)
    gate_status = _gate_status(probe_result, quality_status)
    canonical_bytes, basis, encoding = _canonical_bytes(content, normalized_text)
    content_hash = hash_bytes(canonical_bytes)
    runtime_signature = gate_runtime_signature()
    cache_key = _cache_key(content_hash, runtime_signature)
    root = gate_root(project_root, app_path)
    evidence_excerpt = _evidence_excerpt(
        normalized_text,
        content,
        project_root=project_root,
        app_path=app_path,
        secret_values=secret_values,
    )

    cached = read_cache_entry(root, cache_key)
    decision = _cached_decision(cached, content_hash, runtime_signature)
    if decision is not None:
        if not _cache_matches_inputs(
            decision=decision,
            probe=probe_result,
            quality_status=quality_status,
            gate_status=gate_status,
            merged_reasons=merged_reasons,
        ):
            decision = None
    if decision is not None:
        decision["evidence"] = {
            "excerpt": evidence_excerpt,
            "excerpt_bytes": len(evidence_excerpt.encode("utf-8")),
            "source": "normalized_text" if normalized_text is not None else "raw_bytes",
        }
        decision["cache"] = {"hit": False, "key": cache_key}
        return decision

    chunk_plan = None
    if _chunk_plan_enabled(enable_chunk_plan) and normalized_text is not None:
        chunk_plan = plan_chunks(normalized_text)

    gate_reasons = merged_reasons
    evidence = {
        "excerpt": evidence_excerpt,
        "excerpt_bytes": len(evidence_excerpt.encode("utf-8")),
        "source": "normalized_text" if normalized_text is not None else "raw_bytes",
    }
    normalize_info = {
        "basis": basis,
        "encoding": encoding,
        "bytes": len(canonical_bytes),
        "hash": content_hash,
    }
    if chunk_plan is not None:
        normalize_info["chunk_plan"] = chunk_plan

    fingerprint = {
        "content_hash": content_hash,
        "runtime_signature": runtime_signature,
    }
    decision = {
        "status": gate_status,
        "quality": quality_status,
        "reasons": gate_reasons,
        "probe": probe_result,
        "normalize": normalize_info,
        "evidence": evidence,
        "fingerprint": fingerprint,
        "cache": {"hit": False, "key": cache_key},
    }

    cache_entry = {"fingerprint": fingerprint, "decision": decision}
    write_cache_entry(root, cache_key, cache_entry)

    if gate_status == "blocked":
        quarantine_entry = {
            "status": gate_status,
            "reasons": gate_reasons,
            "probe": probe_result,
            "normalize": normalize_info,
            "evidence": evidence,
            "fingerprint": fingerprint,
        }
        write_quarantine_entry(root, cache_key, quarantine_entry)
        decision["quarantine"] = {"written": True, "key": cache_key}

    return decision


def _cached_decision(cache_entry: dict | None, content_hash: str, runtime_signature: str) -> dict | None:
    if not isinstance(cache_entry, dict):
        return None
    fingerprint = cache_entry.get("fingerprint")
    decision = cache_entry.get("decision")
    if not isinstance(fingerprint, dict) or not isinstance(decision, dict):
        return None
    if fingerprint.get("content_hash") != content_hash:
        return None
    if fingerprint.get("runtime_signature") != runtime_signature:
        return None
    return dict(decision)


def _cache_matches_inputs(
    *,
    decision: dict,
    probe: dict,
    quality_status: str,
    gate_status: str,
    merged_reasons: list[str],
) -> bool:
    cached_status = decision.get("status")
    cached_quality = decision.get("quality")
    cached_reasons = decision.get("reasons")
    if cached_status != gate_status:
        return False
    if cached_quality != quality_status:
        return False
    if list(cached_reasons or []) != list(merged_reasons):
        return False
    cached_probe = decision.get("probe")
    if not isinstance(cached_probe, dict):
        return False
    return cached_probe == probe


def _gate_status(probe: dict, quality_status: str) -> str:
    if probe.get("status") == "block":
        return "blocked"
    if quality_status == "block":
        return "blocked"
    return "allowed"


def _merge_reasons(probe: dict, quality_reasons: Iterable[str]) -> list[str]:
    reasons = list(_text_list(quality_reasons))
    probe_reasons = []
    for key in ("block_reasons", "warn_reasons"):
        probe_reasons.extend(_text_list(probe.get(key)))
    all_reasons = probe_reasons + reasons
    ordered: list[str] = []
    order = list(PROBE_REASON_ORDER) + list(QUALITY_REASON_ORDER)
    seen = set()
    for reason in order:
        if reason in all_reasons and reason not in seen:
            ordered.append(reason)
            seen.add(reason)
    for reason in all_reasons:
        if reason not in seen:
            ordered.append(reason)
            seen.add(reason)
    return ordered


def _text_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item) for item in values if isinstance(item, str) and item]


def _cache_key(content_hash: str, runtime_signature: str) -> str:
    return f"{content_hash}.{runtime_signature}"


def _canonical_bytes(content: bytes, normalized_text: str | None) -> tuple[bytes, str, str]:
    payload = content or b""
    if not payload:
        return b"", "raw_bytes", "utf-8"
    try:
        text = payload.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = payload.decode("latin-1")
        encoding = "latin-1"
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.encode("utf-8"), "raw_bytes", encoding


def _evidence_excerpt(
    normalized_text: str | None,
    content: bytes,
    *,
    project_root: str | None,
    app_path: str | None,
    secret_values: list[str] | None,
) -> str:
    if normalized_text is None:
        text = _decode_for_evidence(content)
    else:
        text = normalized_text
    cleaned = text.replace("\x00", "")
    return preview_text(
        cleaned,
        limit=EVIDENCE_EXCERPT_LIMIT,
        project_root=project_root,
        app_path=app_path,
        secret_values=secret_values,
    )


def _decode_for_evidence(content: bytes) -> str:
    if not content:
        return ""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1", errors="replace")


def _chunk_plan_enabled(flag: bool | None) -> bool:
    if flag is not None:
        return bool(flag)
    value = os.getenv(ENV_CHUNK_PLAN, "")
    value = value.strip().lower()
    return value in {"1", "true", "yes", "on"}


__all__ = ["evaluate_gate"]
