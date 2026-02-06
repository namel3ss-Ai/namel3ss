from __future__ import annotations

import hashlib
import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dump
from namel3ss.runtime.persistence_paths import resolve_persistence_root


CANARY_RESULTS_FILENAME = "canary_results.json"



def canary_results_path(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    allow_create: bool = True,
) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / "observability" / "metrics" / CANARY_RESULTS_FILENAME



def load_canary_results(project_root: str | Path | None, app_path: str | Path | None) -> list[dict[str, object]]:
    path = canary_results_path(project_root, app_path, allow_create=False)
    if path is None or not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        return []
    return [entry for entry in records if isinstance(entry, dict)]



def record_canary_result(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    flow_name: str,
    input_text: str,
    primary_model: str,
    candidate_model: str,
    mode: str,
    primary_output: str,
    candidate_output: str,
    step_count: int,
) -> None:
    path = canary_results_path(project_root, app_path)
    if path is None:
        return
    record = {
        "flow_name": flow_name,
        "input_id": _hash_text(input_text)[:12],
        "primary_model": primary_model,
        "candidate_model": candidate_model,
        "mode": mode,
        "winner": _pick_winner(primary_output, candidate_output),
        "primary_output_hash": _hash_text(primary_output)[:16],
        "candidate_output_hash": _hash_text(candidate_output)[:16],
        "step_count": int(step_count),
    }
    existing = load_canary_results(project_root, app_path)
    existing.append(record)
    existing.sort(key=_sort_key)
    canonical_json_dump(path, {"schema_version": 1, "records": existing}, pretty=True, drop_run_keys=False)



def summarize_canary_results(records: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], dict[str, object]] = {}
    for entry in records:
        primary = str(entry.get("primary_model") or "")
        candidate = str(entry.get("candidate_model") or "")
        mode = str(entry.get("mode") or "")
        key = (primary, candidate, mode)
        item = groups.setdefault(
            key,
            {
                "primary_model": primary,
                "candidate_model": candidate,
                "mode": mode,
                "runs": 0,
                "candidate_wins": 0,
                "primary_wins": 0,
                "ties": 0,
            },
        )
        item["runs"] = int(item.get("runs") or 0) + 1
        winner = str(entry.get("winner") or "tie")
        if winner == "candidate":
            item["candidate_wins"] = int(item.get("candidate_wins") or 0) + 1
        elif winner == "primary":
            item["primary_wins"] = int(item.get("primary_wins") or 0) + 1
        else:
            item["ties"] = int(item.get("ties") or 0) + 1
    values = list(groups.values())
    values.sort(key=lambda item: (str(item.get("primary_model")), str(item.get("candidate_model")), str(item.get("mode"))))
    return values



def _pick_winner(primary_output: str, candidate_output: str) -> str:
    primary = (primary_output or "").strip()
    candidate = (candidate_output or "").strip()
    if primary and not candidate:
        return "primary"
    if candidate and not primary:
        return "candidate"
    if len(candidate) > len(primary):
        return "candidate"
    if len(primary) > len(candidate):
        return "primary"
    if _hash_text(candidate) > _hash_text(primary):
        return "candidate"
    if _hash_text(primary) > _hash_text(candidate):
        return "primary"
    return "tie"



def _sort_key(record: dict[str, object]) -> tuple[str, str, str, str, int]:
    return (
        str(record.get("flow_name") or ""),
        str(record.get("input_id") or ""),
        str(record.get("primary_model") or ""),
        str(record.get("candidate_model") or ""),
        int(record.get("step_count") or 0),
    )



def _hash_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


__all__ = [
    "CANARY_RESULTS_FILENAME",
    "canary_results_path",
    "load_canary_results",
    "record_canary_result",
    "summarize_canary_results",
]
