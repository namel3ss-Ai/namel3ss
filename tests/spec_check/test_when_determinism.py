from __future__ import annotations

from pathlib import Path

from namel3ss.spec_check.builder import build_spec_pack, derive_required_capabilities
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def _build(tmp_path: Path) -> tuple[str, str]:
    program = lower_ir_program(SOURCE)
    build_spec_pack(
        declared_spec=program.spec_version,
        required_capabilities=derive_required_capabilities(program),
        project_root=tmp_path,
    )
    spec_dir = tmp_path / ".namel3ss" / "spec"
    return (
        (spec_dir / "last.json").read_text(encoding="utf-8"),
        (spec_dir / "last.plain").read_text(encoding="utf-8"),
    )


def test_spec_pack_is_deterministic(tmp_path: Path) -> None:
    json_first, plain_first = _build(tmp_path)
    json_second, plain_second = _build(tmp_path)
    assert json_first == json_second
    assert plain_first == plain_second
