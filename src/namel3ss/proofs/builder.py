from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

from namel3ss.cli.builds import load_build_metadata, read_latest_build_id
from namel3ss.cli.targets import parse_target
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader import load_project
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME, lockfile_to_dict, read_lockfile
from namel3ss.runtime.capabilities.report import collect_tool_reports
PROOF_SCHEMA_VERSION = 1
OBSERVE_SCHEMA_VERSION = 1


def build_engine_proof(
    app_path: Path,
    *,
    target: str,
    build_id: str | None = None,
    project_root_override: Path | None = None,
    entry_path_override: Path | None = None,
    entry_relative_override: str | None = None,
    lock_snapshot_override: Dict[str, Any] | None = None,
) -> tuple[str, Dict[str, Any]]:
    project = load_project(app_path)
    project_root = project_root_override or project.app_path.parent
    config = load_config(app_path=project.app_path, root=project_root)
    build_path, build_meta = _resolve_build(project_root, target, build_id)
    lock_snapshot = _normalize_lock_snapshot(lock_snapshot_override or _load_lock_snapshot(project_root))
    identity_summary = _identity_summary(project.program)
    audit_summary = _audit_summary(project.program)
    governance_summary = _governance_summary(project_root)
    entry_path = entry_path_override or project.app_path
    entry_relative = entry_relative_override or _relative_path(project_root, entry_path)
    proof = {
        "schema_version": PROOF_SCHEMA_VERSION,
        "proof_id": None,
        "app": {
            "name": project.app_path.stem,
            "project_root": project_root.resolve().as_posix(),
            "entry_path": entry_path.resolve().as_posix(),
            "entry_relative_path": entry_relative,
            "content_hash": _hash_sources(project.sources, project_root),
        },
        "engine": {
            "target": parse_target(target).name,
        },
        "persistence": _persistence_summary(config, project_root),
        "capsules": _capsule_summary(project, lock_snapshot.get("lockfile")),
        "capabilities": {"tools": collect_tool_reports(project_root, config, project.program.tools)},
        "packages": lock_snapshot,
        "identity": identity_summary,
        "governance": governance_summary,
        "audit": audit_summary,
        "build": _build_summary(build_path, build_meta, project_root),
        "schema_versions": {
            "lock": lock_snapshot.get("lockfile_version"),
            "observe": OBSERVE_SCHEMA_VERSION,
        },
        "timestamp": time.time(),
    }
    proof_id = _proof_id(proof)
    proof["proof_id"] = proof_id
    return proof_id, proof


def _resolve_build(project_root: Path, target: str, build_id: str | None) -> tuple[Path | None, Dict[str, Any]]:
    chosen = build_id or read_latest_build_id(project_root, target)
    if not chosen:
        return None, {}
    try:
        return load_build_metadata(project_root, target, chosen)
    except Namel3ssError:
        return None, {}


def _load_lock_snapshot(project_root: Path) -> Dict[str, Any]:
    path = project_root / LOCKFILE_FILENAME
    if not path.exists():
        return {
            "status": "missing",
            "path": path.as_posix(),
            "lockfile_version": None,
            "lockfile": None,
            "packages": [],
        }
    try:
        lock = read_lockfile(project_root)
        payload = lockfile_to_dict(lock)
        return {
            "status": "present",
            "path": path.as_posix(),
            "lockfile_version": payload.get("lockfile_version"),
            "lockfile": payload,
            "packages": payload.get("packages", []),
        }
    except Namel3ssError as err:
        return {
            "status": "invalid",
            "path": path.as_posix(),
            "lockfile_version": None,
            "lockfile": None,
            "packages": [],
            "error": str(err),
        }


def _normalize_lock_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {
            "status": "missing",
            "path": None,
            "lockfile_version": None,
            "lockfile": None,
            "packages": [],
        }
    normalized = dict(snapshot)
    lockfile = normalized.get("lockfile") if isinstance(normalized.get("lockfile"), dict) else None
    if lockfile:
        lockfile = dict(lockfile)
        lockfile["packages"] = _sorted_packages(lockfile.get("packages"))
        normalized["lockfile"] = lockfile
        normalized.setdefault("lockfile_version", lockfile.get("lockfile_version"))
        normalized.setdefault("packages", lockfile.get("packages", []))
    normalized["packages"] = _sorted_packages(normalized.get("packages"))
    normalized.setdefault("lockfile_version", normalized.get("lockfile_version"))
    return normalized


def _identity_summary(program) -> Dict[str, Any]:
    identity = getattr(program, "identity", None)
    name = getattr(identity, "name", None) if identity else None
    flows_requires = [flow.name for flow in program.flows if getattr(flow, "requires", None) is not None]
    pages_requires = [page.name for page in program.pages if getattr(page, "requires", None) is not None]
    tenant_scoped = [rec.name for rec in program.records if getattr(rec, "tenant_key", None)]
    return {
        "identities": [name] if name else [],
        "requires": {
            "flows": sorted(flows_requires),
            "pages": sorted(pages_requires),
            "flow_count": len(flows_requires),
            "page_count": len(pages_requires),
        },
        "tenant_scoping": {
            "records": sorted(tenant_scoped),
            "count": len(tenant_scoped),
        },
    }


def _audit_summary(program) -> Dict[str, Any]:
    audited_flows = sorted(flow.name for flow in program.flows if getattr(flow, "audited", False))
    return {
        "audited_flows": audited_flows,
        "count": len(audited_flows),
    }


def _governance_summary(project_root: Path) -> Dict[str, Any]:
    path = project_root / ".namel3ss" / "verify.json"
    if not path.exists():
        return {"checks": [], "status": "unknown"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"checks": [], "status": "unknown"}
    checks = data.get("checks", []) if isinstance(data, dict) else []
    status = data.get("status") if isinstance(data, dict) else "unknown"
    return {"checks": checks, "status": status}


def _capsule_summary(project, lock_snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    modules = project.modules or {}
    lock_packages = {pkg.get("name"): pkg for pkg in (lock_snapshot or {}).get("packages", []) if isinstance(pkg, dict)}
    module_entries = []
    for name in sorted(modules.keys()):
        info = modules[name]
        source = _module_source(info.path, name, lock_packages.get(name))
        exports = info.exports.kinds()
        exports = {kind: exports[kind] for kind in sorted(exports.keys())}
        module_entries.append(
            {
                "name": name,
                "source": source,
                "exports": exports,
            }
        )
    graph = project.graph
    nodes = sorted(list(graph.nodes))
    edges = sorted(list(graph.edges), key=lambda item: (item[0], item[1]))
    return {
        "graph": {
            "nodes": nodes,
            "edges": [{"from": src, "to": dst} for src, dst in edges],
        },
        "modules": module_entries,
    }


def _sorted_packages(packages: object) -> list:
    if not isinstance(packages, list):
        return []
    if all(isinstance(pkg, dict) and "name" in pkg for pkg in packages):
        return sorted(packages, key=lambda pkg: str(pkg.get("name", "")))
    return list(packages)


def _module_source(path: Path, name: str, lock_entry: Dict[str, Any] | None) -> Dict[str, Any]:
    path_str = path.resolve().as_posix()
    if "/packages/" in path_str.replace("\\", "/"):
        source = lock_entry.get("source") if isinstance(lock_entry, dict) else None
        return {"kind": "package", "name": name, "source": source or "unknown"}
    return {"kind": "local", "path": path_str}


def _persistence_summary(config, project_root: Path) -> Dict[str, Any]:
    target = (config.persistence.target or "memory").lower()
    descriptor: Dict[str, Any] = {"target": target}
    if target == "sqlite":
        db_path = config.persistence.db_path or ".namel3ss/data.db"
        descriptor["descriptor"] = _relative_path(project_root, Path(db_path))
    elif target == "postgres":
        descriptor["descriptor"] = _redacted_postgres_descriptor(config.persistence.database_url)
    elif target == "edge":
        descriptor["descriptor"] = "edge-kv"
    else:
        descriptor["descriptor"] = None
    return descriptor


def _redacted_postgres_descriptor(url: str | None) -> Dict[str, Any]:
    if not url:
        return {"host": None, "database": None, "port": None}
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        return {"host": None, "database": None, "port": None}
    database = parsed.path.lstrip("/") if parsed.path else None
    return {"host": parsed.hostname, "database": database, "port": parsed.port}


def _build_summary(build_path: Path | None, build_meta: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    if not build_meta:
        return {"build_id": None, "artifact_path": None, "snapshot_hash": None}
    build_id = build_meta.get("build_id")
    artifact = build_path.resolve().as_posix() if build_path else None
    return {
        "build_id": build_id,
        "artifact_path": _relative_path(project_root, Path(artifact)) if artifact else None,
        "snapshot_hash": build_id,
    }


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _hash_sources(sources: Dict[Path, str], project_root: Path) -> str:
    h = hashlib.sha256()
    for path, text in sorted(sources.items(), key=lambda item: item[0].as_posix()):
        rel = _relative_path(project_root, path)
        h.update(rel.encode("utf-8"))
        h.update(text.encode("utf-8"))
    return h.hexdigest()


def _proof_id(proof: Dict[str, Any]) -> str:
    payload = dict(proof)
    payload.pop("timestamp", None)
    payload.pop("proof_id", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"proof-{digest[:12]}"


__all__ = ["PROOF_SCHEMA_VERSION", "OBSERVE_SCHEMA_VERSION", "build_engine_proof"]
