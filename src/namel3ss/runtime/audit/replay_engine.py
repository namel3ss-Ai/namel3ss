from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from namel3ss.runtime.audit.run_artifact import (
    compute_component_hash,
    compute_integrity_hash,
    compute_run_id,
    normalize_run_artifact,
)


def replay_run_artifact(artifact: Mapping[str, object]) -> dict[str, object]:
    normalized = normalize_run_artifact(artifact)
    if not normalized:
        return {
            "ok": False,
            "mismatches": [
                {
                    "field": "artifact",
                    "expected": "non-empty run artifact object",
                    "actual": "empty or invalid",
                }
            ],
        }
    stored_run_id = str(normalized.get("run_id") or "")
    computed_run_id = compute_run_id(normalized)
    stored_checksums = _mapping_or_empty(normalized.get("checksums"))
    replayed_checksums = _replayed_checksums(normalized)
    mismatches: list[dict[str, object]] = []
    if stored_run_id != computed_run_id:
        mismatches.append(_mismatch("run_id", computed_run_id, stored_run_id))
    for key in ("inputs_hash", "retrieval_trace_hash", "prompt_hash", "capability_usage_hash", "output_hash"):
        expected = str(replayed_checksums.get(key) or "")
        actual = str(stored_checksums.get(key) or "")
        if actual != expected:
            mismatches.append(_mismatch(f"checksums.{key}", expected, actual))
    return {
        "ok": len(mismatches) == 0,
        "run_id": stored_run_id,
        "computed_run_id": computed_run_id,
        "integrity_hash": compute_integrity_hash(normalized),
        "mismatches": mismatches,
        "replayed_checksums": replayed_checksums,
    }


def replay_run_artifact_file(path: str | Path) -> dict[str, object]:
    artifact_path = Path(path).expanduser().resolve()
    artifact = _read_artifact(artifact_path)
    payload = replay_run_artifact(artifact)
    payload["artifact_path"] = artifact_path.as_posix()
    return payload


def _replayed_checksums(artifact: Mapping[str, object]) -> dict[str, str]:
    inputs_hash = _checksum(artifact.get("inputs"))
    retrieval_hash = _checksum(artifact.get("retrieval_trace"))
    prompt = _mapping_or_empty(artifact.get("prompt"))
    prompt_hash = str(prompt.get("hash") or "")
    if not prompt_hash:
        prompt_text = str(prompt.get("text") or "")
        if prompt_text:
            prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
    capability_usage_hash = _checksum(artifact.get("capability_usage"))
    output_hash = _checksum(artifact.get("output"))
    return {
        "inputs_hash": inputs_hash,
        "retrieval_trace_hash": retrieval_hash,
        "prompt_hash": prompt_hash,
        "capability_usage_hash": capability_usage_hash,
        "output_hash": output_hash,
    }


def _checksum(value: object) -> str:
    return compute_component_hash(value)


def _read_artifact(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(payload, dict):
        return {str(key): payload[key] for key in payload.keys()}
    return {}


def _mismatch(field: str, expected: object, actual: object) -> dict[str, object]:
    return {
        "field": field,
        "expected": expected,
        "actual": actual,
    }


def _mapping_or_empty(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): value[key] for key in value.keys()}


__all__ = ["replay_run_artifact", "replay_run_artifact_file"]
