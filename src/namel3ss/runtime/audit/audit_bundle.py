from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from namel3ss.determinism import canonical_json_dumps
from namel3ss.runtime.artifact_contract import ArtifactContract
from namel3ss.runtime.audit.run_artifact import (
    RUN_ARTIFACT_SCHEMA_VERSION,
    compute_integrity_hash,
    normalize_run_artifact,
)


AUDIT_BUNDLE_SCHEMA_VERSION = "audit_bundle@1"


def write_audit_bundle(project_root: str | Path, artifact: Mapping[str, object]) -> dict[str, object]:
    contract = _artifact_contract(project_root)
    normalized = normalize_run_artifact(artifact)
    if not normalized:
        raise ValueError("Run artifact is empty.")
    run_id = str(normalized.get("run_id") or "").strip()
    if not run_id:
        raise ValueError("Run artifact is missing run_id.")
    schema_version = str(normalized.get("schema_version") or "").strip()
    if schema_version != RUN_ARTIFACT_SCHEMA_VERSION:
        raise ValueError(f"Run artifact schema_version must be {RUN_ARTIFACT_SCHEMA_VERSION}.")
    integrity_hash = compute_integrity_hash(normalized)
    run_artifact_rel = f"audit/{run_id}/run_artifact.json"
    bundle_rel = f"audit/{run_id}/bundle.json"
    run_artifact_path = contract.prepare_file(run_artifact_rel)
    bundle_path = contract.prepare_file(bundle_rel)
    bundle = {
        "schema_version": AUDIT_BUNDLE_SCHEMA_VERSION,
        "run_id": run_id,
        "integrity_hash": integrity_hash,
        "run_artifact_path": run_artifact_rel,
        "bundle_path": bundle_rel,
    }
    _write_immutable_json(run_artifact_path, normalized)
    _write_immutable_json(bundle_path, bundle)
    _write_json(contract.prepare_file("audit/last/run_artifact.json"), normalized)
    _write_json(contract.prepare_file("audit/last/bundle.json"), bundle)
    return bundle


def load_run_artifact(
    project_root: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, object] | None:
    contract = _artifact_contract(project_root)
    relative = "audit/last/run_artifact.json"
    if isinstance(run_id, str) and run_id.strip():
        relative = f"audit/{run_id.strip()}/run_artifact.json"
    path = contract.resolve(relative)
    if not path.exists():
        return None
    return _read_json(path)


def list_audit_bundles(project_root: str | Path, *, limit: int | None = 25) -> list[dict[str, object]]:
    contract = _artifact_contract(project_root)
    audit_root = contract.resolve("audit")
    if not audit_root.exists() or not audit_root.is_dir():
        return []
    bundles: list[dict[str, object]] = []
    for child in sorted(audit_root.iterdir(), key=lambda item: item.name):
        if not child.is_dir():
            continue
        run_id = child.name.strip()
        if not run_id or run_id == "last":
            continue
        bundle = _read_json(child / "bundle.json")
        if not bundle:
            continue
        bundles.append(bundle)
    if limit is None or limit <= 0:
        return bundles
    return bundles[:limit]


def resolve_audit_artifact_path(project_root: str | Path, *, run_id: str | None = None) -> Path:
    contract = _artifact_contract(project_root)
    if isinstance(run_id, str) and run_id.strip():
        return contract.resolve(f"audit/{run_id.strip()}/run_artifact.json")
    return contract.resolve("audit/last/run_artifact.json")


def _artifact_contract(project_root: str | Path) -> ArtifactContract:
    root = Path(project_root).resolve()
    return ArtifactContract(root / ".namel3ss")


def _write_immutable_json(path: Path, payload: Mapping[str, object]) -> None:
    serialized = canonical_json_dumps(payload, pretty=True, drop_run_keys=False)
    if path.exists():
        existing = canonical_json_dumps(_read_json(path), pretty=True, drop_run_keys=False)
        if existing != serialized:
            raise ValueError(f"Immutable audit file already exists with different content: {path}")
        return
    path.write_text(serialized, encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(canonical_json_dumps(payload, pretty=True, drop_run_keys=False), encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(data, dict):
        return {str(key): data[key] for key in data.keys()}
    return {}


__all__ = [
    "AUDIT_BUNDLE_SCHEMA_VERSION",
    "list_audit_bundles",
    "load_run_artifact",
    "resolve_audit_artifact_path",
    "write_audit_bundle",
]
