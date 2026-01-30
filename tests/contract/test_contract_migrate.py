from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_plan(kind: str) -> dict:
    result = subprocess.run(
        [sys.executable, "tools/contract_migrate.py", "--kind", kind],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_contract_migration_plan_is_deterministic() -> None:
    first = _run_plan("grammar")
    second = _run_plan("grammar")
    assert first == second
    assert first.get("status") == "none"
    assert first.get("changes") == []
    assert first.get("before_hash") == first.get("after_hash")


def test_contract_migration_targets_are_repo_relative() -> None:
    for kind in ["grammar", "schema", "templates"]:
        plan = _run_plan(kind)
        target = str(plan.get("target", ""))
        assert target
        assert not target.startswith("/")
        assert ":" not in target
        assert Path(target).as_posix() == target
