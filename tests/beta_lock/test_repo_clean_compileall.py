from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from namel3ss.beta_lock.repo_clean import repo_dirty_entries


def test_compileall_does_not_dirty_repo() -> None:
    root = Path(__file__).resolve().parents[2]
    baseline = set(repo_dirty_entries(root))
    cmd = (
        sys.executable,
        "-m",
        "compileall",
        "src",
        "-q",
        "-x",
        r".*namel3ss/runtime/build.*",
    )
    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr or result.stdout
    dirty = set(repo_dirty_entries(root))
    new_entries = sorted(dirty - baseline)
    assert not new_entries, "Repository dirtied by compileall:\n" + "\n".join(new_entries)
