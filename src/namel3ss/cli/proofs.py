from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from namel3ss.cli.targets_store import ensure_dir, read_json, write_json


PROOFS_DIR = ".namel3ss/proofs"
ACTIVE_PROOF_FILE = ".namel3ss/active_proof.json"
PROOF_STATE_FILE = ".namel3ss/proof_state.json"


def proof_dir(project_root: Path) -> Path:
    return project_root / PROOFS_DIR


def proof_path(project_root: Path, proof_id: str) -> Path:
    return proof_dir(project_root) / f"{proof_id}.json"


def write_proof(project_root: Path, proof_id: str, payload: Dict[str, Any]) -> Path:
    path = proof_path(project_root, proof_id)
    write_json(path, payload)
    return path


def read_proof(project_root: Path, proof_id: str) -> Dict[str, Any]:
    return read_json(proof_path(project_root, proof_id))


def active_proof_path(project_root: Path) -> Path:
    return project_root / ACTIVE_PROOF_FILE


def load_active_proof(project_root: Path) -> Dict[str, Any]:
    path = active_proof_path(project_root)
    if not path.exists():
        return {}
    return read_json(path)


def record_active_proof(project_root: Path, proof_id: str, target: str, build_id: str | None) -> Dict[str, Any]:
    state = load_proof_state(project_root)
    current = state.get("active") or {}
    state["previous"] = {
        "proof_id": current.get("proof_id"),
        "target": current.get("target"),
        "build_id": current.get("build_id"),
    }
    state["active"] = {"proof_id": proof_id, "target": target, "build_id": build_id}
    write_proof_state(project_root, state)
    write_json(active_proof_path(project_root), state["active"])
    return state


def record_proof_rollback(project_root: Path) -> Dict[str, Any]:
    state = load_proof_state(project_root)
    prev = state.get("previous") or {}
    state["active"] = {
        "proof_id": prev.get("proof_id"),
        "target": prev.get("target"),
        "build_id": prev.get("build_id"),
    }
    state["previous"] = {"proof_id": None, "target": None, "build_id": None}
    write_proof_state(project_root, state)
    write_json(active_proof_path(project_root), state["active"])
    return state


def load_proof_state(project_root: Path) -> Dict[str, Any]:
    path = project_root / PROOF_STATE_FILE
    if not path.exists():
        return {
            "active": {"proof_id": None, "target": None, "build_id": None},
            "previous": {"proof_id": None, "target": None, "build_id": None},
        }
    return read_json(path)


def write_proof_state(project_root: Path, state: Dict[str, Any]) -> None:
    path = project_root / PROOF_STATE_FILE
    ensure_dir(path.parent)
    write_json(path, state)


__all__ = [
    "ACTIVE_PROOF_FILE",
    "PROOFS_DIR",
    "PROOF_STATE_FILE",
    "active_proof_path",
    "load_active_proof",
    "load_proof_state",
    "proof_dir",
    "proof_path",
    "record_active_proof",
    "record_proof_rollback",
    "read_proof",
    "write_proof",
    "write_proof_state",
]
