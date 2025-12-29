from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from namel3ss.outcome.model import OutcomePack, RunOutcome


def normalize_outcome(outcome: RunOutcome) -> RunOutcome:
    return RunOutcome(
        status=outcome.status,
        flow_name=outcome.flow_name,
        store=outcome.store,
        state=outcome.state,
        memory=outcome.memory,
        record_changes_count=int(outcome.record_changes_count),
        execution_steps_count=int(outcome.execution_steps_count),
        traces_count=int(outcome.traces_count),
        what_did_not_happen=normalize_bullets(outcome.what_did_not_happen),
    )


def normalize_bullets(items: Iterable[str]) -> tuple[str, ...]:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return tuple(sorted(dict.fromkeys(cleaned)))


def write_outcome_artifacts(root: Path, pack: OutcomePack, plain_text: str, what_text: str) -> None:
    outcome_dir = root / ".namel3ss" / "outcome"
    outcome_dir.mkdir(parents=True, exist_ok=True)
    (outcome_dir / "last.json").write_text(_stable_json(pack.as_dict()), encoding="utf-8")
    (outcome_dir / "last.plain").write_text(plain_text.rstrip() + "\n", encoding="utf-8")
    (outcome_dir / "last.what.txt").write_text(what_text.rstrip() + "\n", encoding="utf-8")


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


__all__ = ["normalize_bullets", "normalize_outcome", "write_outcome_artifacts"]
