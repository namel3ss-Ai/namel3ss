import re
import os
import subprocess
import sys
from pathlib import Path


def test_version_flag():
    env = os.environ.copy()
    root = Path(__file__).resolve().parents[2]
    env["PYTHONPATH"] = str(root / "src")
    cmd = [sys.executable, "-m", "namel3ss.cli.main", "--version"]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=root)
    assert proc.returncode == 0
    out = proc.stdout.strip()
    assert out.startswith("namel3ss ")
    assert re.search(r"\d+\.\d+\.\d+", out)
