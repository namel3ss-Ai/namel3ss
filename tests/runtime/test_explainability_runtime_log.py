from __future__ import annotations

import json
from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.pipelines.registry import pipeline_contracts
from namel3ss.runtime.executor import Executor
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

capabilities:
  streaming

ai "assistant":
  provider is "mock"
  model is "mock-model"

flow "demo":
  ask ai "assistant" with stream: true and input: "hello world" as reply
  return reply
'''


def test_runtime_persists_deterministic_explain_log(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    app.write_text(SOURCE, encoding="utf-8")
    result_a = _run_demo(SOURCE, project_root=tmp_path, app_path=app)
    assert isinstance(result_a.last_value, str)
    explain_path = tmp_path / ".namel3ss" / "explain" / "last_explain.json"
    assert explain_path.exists()
    first_payload = json.loads(explain_path.read_text(encoding="utf-8"))
    assert first_payload["entry_count"] >= 3
    generation = [entry for entry in first_payload["entries"] if entry.get("stage") == "generation"]
    assert generation
    assert generation[0]["event_type"] == "start"
    assert isinstance(generation[0].get("seed"), int)
    streaming = [entry for entry in first_payload["entries"] if entry.get("stage") == "streaming"]
    assert streaming
    assert [entry.get("event_index") for entry in first_payload["entries"]] == list(
        range(1, len(first_payload["entries"]) + 1)
    )

    result_b = _run_demo(SOURCE, project_root=tmp_path, app_path=app)
    assert result_b.last_value == result_a.last_value
    second_payload = json.loads(explain_path.read_text(encoding="utf-8"))
    assert second_payload["replay_hash"] == first_payload["replay_hash"]
    assert second_payload["entries"] == first_payload["entries"]


def test_runtime_explain_log_redacts_user_data_when_enabled(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    app.write_text(SOURCE, encoding="utf-8")
    config = tmp_path / "namel3ss.toml"
    config.write_text(
        (
            "[determinism]\n"
            "explain = true\n"
            "redact_user_data = true\n"
        ),
        encoding="utf-8",
    )
    _run_demo(SOURCE, project_root=tmp_path, app_path=app)
    explain_path = tmp_path / ".namel3ss" / "explain" / "last_explain.json"
    payload = json.loads(explain_path.read_text(encoding="utf-8"))
    generation_start = next(
        entry for entry in payload["entries"] if entry.get("stage") == "generation" and entry.get("event_type") == "start"
    )
    generation_finish = next(
        entry
        for entry in payload["entries"]
        if entry.get("stage") == "generation" and entry.get("event_type") == "finish"
    )
    assert generation_start["inputs"]["user_input"] == "(redacted)"
    assert generation_finish["outputs"]["output"] == "(redacted)"


def _run_demo(source: str, *, project_root: Path, app_path: Path):
    program = lower_ir_program(source)
    flow = next(entry for entry in program.flows if entry.name == "demo")
    schemas = {schema.name: schema for schema in program.records}
    config = load_config(app_path=app_path, root=project_root)
    executor = Executor(
        flow,
        schemas=schemas,
        ai_profiles=program.ais,
        agents=program.agents,
        tools=program.tools,
        functions=program.functions,
        flows={entry.name: entry for entry in program.flows},
        flow_contracts=getattr(program, "flow_contracts", {}) or {},
        pipeline_contracts=pipeline_contracts(),
        capabilities=getattr(program, "capabilities", ()),
        config=config,
        project_root=project_root.as_posix(),
        app_path=app_path.as_posix(),
    )
    return executor.run()
