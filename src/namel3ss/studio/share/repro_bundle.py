from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from namel3ss.determinism import canonical_json_dumps


REPRO_BUNDLE_SCHEMA_VERSION = "studio_repro_bundle@1"


def build_repro_bundle(
    *,
    run_artifact: Mapping[str, object],
    workspace_id: str,
    session_id: str,
) -> dict[str, object]:
    artifact = _mapping_or_empty(run_artifact)
    run_id = _text(artifact.get("run_id"))
    program = _mapping_or_empty(artifact.get("program"))
    return {
        "schema_version": REPRO_BUNDLE_SCHEMA_VERSION,
        "workspace_id": _text(workspace_id),
        "session_id": _text(session_id),
        "run_id": run_id,
        "repro_path": f"studio/repro/{run_id}.json" if run_id else "",
        "app_hash": _text(program.get("app_hash")),
        "program_entrypoint": _text(program.get("entrypoint")),
        "input_snapshot": _mapping_or_empty(artifact.get("inputs")),
        "prompt": _mapping_or_empty(artifact.get("prompt")),
        "output": artifact.get("output"),
        "retrieval_trace": _list_of_maps(artifact.get("retrieval_trace")),
        "trust_score_details": _mapping_or_empty(artifact.get("trust_score_details")),
        "runtime_errors": _list_of_maps(artifact.get("runtime_errors")),
    }


def write_repro_bundle(project_root: str | Path, bundle: Mapping[str, object]) -> Path:
    normalized = _mapping_or_empty(bundle)
    run_id = _text(normalized.get("run_id"))
    if not run_id:
        raise ValueError("Repro bundle requires run_id.")
    target = _bundle_path(project_root, run_id=run_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    serialized = canonical_json_dumps(normalized, pretty=True, drop_run_keys=False)
    target.write_text(serialized, encoding="utf-8")
    latest = _bundle_path(project_root, run_id="latest")
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(serialized, encoding="utf-8")
    return target


def load_repro_bundle(project_root: str | Path, *, run_id: str | None = None) -> dict[str, object] | None:
    target = _bundle_path(project_root, run_id=run_id or "latest")
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    normalized = {str(key): payload[key] for key in payload.keys()}
    schema_version = _text(normalized.get("schema_version"))
    if schema_version != REPRO_BUNDLE_SCHEMA_VERSION:
        return None
    return normalized


def _bundle_path(project_root: str | Path, *, run_id: str) -> Path:
    root = Path(project_root).resolve()
    safe_run_id = _text(run_id)
    return root / ".namel3ss" / "studio" / "repro" / f"{safe_run_id}.json"


def _mapping_or_empty(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return {str(key): value[key] for key in value.keys()}
    return {}


def _list_of_maps(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    output: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, Mapping):
            output.append({str(key): item[key] for key in item.keys()})
    return output


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


__all__ = [
    "REPRO_BUNDLE_SCHEMA_VERSION",
    "build_repro_bundle",
    "load_repro_bundle",
    "write_repro_bundle",
]
