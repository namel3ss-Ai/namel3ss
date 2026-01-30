from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFIXES = (
    "namel3ss.ingestion",
    "namel3ss.module_loader",
    "namel3ss.providers",
    "namel3ss.runtime",
    "namel3ss.studio",
    "namel3ss.ui",
)


def _run_cli(args: list[str]) -> dict:
    script = "\n".join(
        [
            "import json",
            "import io",
            "import sys",
            "from contextlib import redirect_stdout",
            "from namel3ss.cli import main as cli_main",
            f"args = {args!r}",
            f"prefixes = {PREFIXES!r}",
            "buffer = io.StringIO()",
            "with redirect_stdout(buffer):",
            "    try:",
            "        code = cli_main.main(args)",
            "    except SystemExit as exc:",
            "        code = exc.code or 0",
            "loaded = sorted(name for name in sys.modules if name.startswith(prefixes))",
            "print(json.dumps({'code': code, 'loaded': loaded}))",
        ]
    )
    env = os.environ.copy()
    env.pop("N3_PROFILE", None)
    src_path = str(ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not existing else f"{src_path}{os.pathsep}{existing}"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = result.stdout.strip()
    assert payload, result.stderr
    return json.loads(payload)


def test_help_and_version_are_lazy() -> None:
    help_payload = _run_cli(["--help"])
    assert help_payload["code"] == 0
    assert help_payload["loaded"] == []
    version_payload = _run_cli(["--version"])
    assert version_payload["code"] == 0
    assert version_payload["loaded"] == []
