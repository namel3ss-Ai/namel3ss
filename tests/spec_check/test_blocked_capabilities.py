from __future__ import annotations

from pathlib import Path

from namel3ss.spec_check import builder
from namel3ss.spec_check.api import check_spec_for_program
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with input: "hi" as reply
  return reply
'''


def test_blocked_capabilities_writes_artifacts(tmp_path: Path, monkeypatch) -> None:
    program = lower_ir_program(SOURCE)
    setattr(program, "project_root", tmp_path)
    monkeypatch.setitem(builder.SPEC_CAPABILITIES, "1.0", frozenset({"records_v1"}))

    pack = check_spec_for_program(program, program.spec_version)
    assert pack.decision.status == "blocked"
    assert "ai_v1" in pack.decision.unsupported_capabilities

    spec_dir = tmp_path / ".namel3ss" / "spec"
    assert (spec_dir / "last.json").exists()
    assert (spec_dir / "last.plain").exists()
