from __future__ import annotations

from pathlib import Path

from namel3ss.spec_check.api import check_spec_for_program
from tests.conftest import lower_ir_program


SOURCE = '''spec is "9.9"

flow "demo":
  return "ok"
'''


def test_blocked_version_writes_artifacts(tmp_path: Path) -> None:
    program = lower_ir_program(SOURCE)
    setattr(program, "project_root", tmp_path)
    pack = check_spec_for_program(program, program.spec_version)
    assert pack.decision.status == "blocked"

    spec_dir = tmp_path / ".namel3ss" / "spec"
    assert (spec_dir / "last.json").exists()
    assert (spec_dir / "last.plain").exists()
    assert (spec_dir / "last.when.txt").exists()
    text = (spec_dir / "last.plain").read_text(encoding="utf-8")
    assert "blocked" in text.lower()
