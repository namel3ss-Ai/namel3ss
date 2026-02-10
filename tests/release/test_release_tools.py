from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )


def test_ga_checklist_json_output_is_deterministic() -> None:
    first = _run(["tools/release/checklist.py", "--json"])
    second = _run(["tools/release/checklist.py", "--json"])
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout
    payload = json.loads(first.stdout)
    assert payload["ok"] is True
    assert [item["name"] for item in payload["checks"]] == sorted(item["name"] for item in payload["checks"])


def test_release_changelog_export_is_reproducible(tmp_path: Path) -> None:
    out_a = tmp_path / "changelog_a.json"
    out_b = tmp_path / "changelog_b.json"
    first = _run(["tools/release/changelog.py", "--json", "--output", str(out_a)])
    second = _run(["tools/release/changelog.py", "--json", "--output", str(out_b)])
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    text_a = out_a.read_text(encoding="utf-8")
    text_b = out_b.read_text(encoding="utf-8")
    assert text_a == text_b
    payload = json.loads(text_a)
    assert "version" in payload
    assert payload["line_count"] >= 1
    assert len(payload["sha256"]) == 64
