from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.artifact_contract import ArtifactContract


STATE_PATH = "migrations/state.json"
PLANS_DIR = "migrations/plans"


@dataclass(frozen=True)
class MigrationState:
    last_plan_id: str | None = None
    applied_plan_id: str | None = None

    def as_dict(self) -> dict:
        return {
            "last_plan_id": self.last_plan_id,
            "applied_plan_id": self.applied_plan_id,
        }


def load_state(project_root: str | Path) -> MigrationState:
    path = _contract(project_root).resolve(STATE_PATH)
    if not path.exists():
        return MigrationState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(_invalid_state_message()) from err
    if not isinstance(data, dict):
        raise Namel3ssError(_invalid_state_message())
    return MigrationState(
        last_plan_id=_safe_id(data.get("last_plan_id")),
        applied_plan_id=_safe_id(data.get("applied_plan_id")),
    )


def write_state(project_root: str | Path, state: MigrationState) -> Path:
    contract = _contract(project_root)
    path = contract.prepare_file(STATE_PATH)
    payload = canonical_json_dumps(state.as_dict(), pretty=True, drop_run_keys=False)
    path.write_text(payload, encoding="utf-8")
    return path


def write_plan(project_root: str | Path, plan_id: str, payload: dict) -> Path:
    contract = _contract(project_root)
    path = contract.prepare_file(f"{PLANS_DIR}/{plan_id}.json")
    plan_json = canonical_json_dumps(payload, pretty=True, drop_run_keys=False)
    path.write_text(plan_json, encoding="utf-8")
    return path


def load_plan(project_root: str | Path, plan_id: str) -> dict | None:
    if not plan_id:
        return None
    path = _contract(project_root).resolve(f"{PLANS_DIR}/{plan_id}.json")
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(_invalid_plan_message()) from err
    if not isinstance(data, dict):
        raise Namel3ssError(_invalid_plan_message())
    return data


def load_last_plan(project_root: str | Path) -> dict | None:
    state = load_state(project_root)
    if not state.last_plan_id:
        return None
    return load_plan(project_root, state.last_plan_id)


def _contract(project_root: str | Path) -> ArtifactContract:
    root = Path(project_root) / ".namel3ss"
    return ArtifactContract(root)


def _safe_id(value: object) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    return text or None


def _invalid_state_message() -> str:
    return build_guidance_message(
        what="Migration state is invalid.",
        why="The migration state file is not valid JSON.",
        fix="Delete the migration state file and re-run migrate.",
        example="rm .namel3ss/migrations/state.json",
    )


def _invalid_plan_message() -> str:
    return build_guidance_message(
        what="Migration plan is invalid.",
        why="The migration plan file is not valid JSON.",
        fix="Regenerate the migration plan.",
        example="n3 migrate plan",
    )


__all__ = [
    "MigrationState",
    "load_last_plan",
    "load_plan",
    "load_state",
    "write_plan",
    "write_state",
]
