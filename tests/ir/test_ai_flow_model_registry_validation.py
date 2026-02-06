from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse


def _write_registry(tmp_path: Path, *, status: str = "active") -> None:
    (tmp_path / "models_registry.yaml").write_text(
        (
            "models:\n"
            "  - name: gpt-4\n"
            "    version: \"1.0\"\n"
            "    provider: openai\n"
            "    domain: general\n"
            "    tokens_per_second: 10\n"
            "    cost_per_token: 0.00001\n"
            "    privacy_level: standard\n"
            f"    status: {status}\n"
        ),
        encoding="utf-8",
    )


def _parse_with_project(source: str, app_path: Path):
    program = parse(source)
    program.project_root = str(app_path.parent)
    program.app_path = str(app_path)
    return program


def test_model_registry_validation_accepts_registered_model(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    app.write_text("", encoding="utf-8")
    _write_registry(tmp_path, status="active")
    source = '''
spec is "1.0"

qa "answer_question":
  model is "gpt-4"
  prompt is "Qn: " + input.question + "\\nCtx: " + input.context + "\\nAns: "
  output:
    ans is text
'''.lstrip()
    program = _parse_with_project(source, app)
    lowered = lower_program(program)
    assert any(flow.name == "answer_question" for flow in lowered.ai_flows)


def test_model_registry_validation_rejects_deprecated_model(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    app.write_text("", encoding="utf-8")
    _write_registry(tmp_path, status="deprecated")
    source = '''
spec is "1.0"

summarise "summary_flow":
  model is "gpt-4"
  prompt is "Summarise: " + input.text
'''.lstrip()
    program = _parse_with_project(source, app)
    with pytest.raises(Namel3ssError) as exc:
        lower_program(program)
    assert "deprecated model" in exc.value.message


def test_chain_validation_rejects_unknown_step_flow(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    app.write_text("", encoding="utf-8")
    source = '''
spec is "1.0"

chain "broken_chain":
  steps:
    - call summarise "missing_flow" with input.text
  output:
    result is text
'''.lstrip()
    program = _parse_with_project(source, app)
    with pytest.raises(Namel3ssError) as exc:
        lower_program(program)
    assert 'unknown flow "missing_flow"' in exc.value.message
