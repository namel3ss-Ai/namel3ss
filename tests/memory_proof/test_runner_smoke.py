from pathlib import Path

from namel3ss.runtime.memory.proof import load_scenario
from namel3ss.runtime.memory.proof.runner import run_scenario


def test_runner_smoke(tmp_path: Path) -> None:
    scenario_path = tmp_path / "001_smoke.yaml"
    scenario_path.write_text(
        """
name: "Smoke scenario"
ai_profile:
  name: "assistant"
  memory:
    short_term: 1
    semantic: false
    profile: false
steps:
  - record:
    input: "Hello"
    output: "ok"
    tool_events: []
  - recall:
    input: "Hello"
""".lstrip(),
        encoding="utf-8",
    )
    scenario = load_scenario(scenario_path)
    run = run_scenario(scenario)
    assert run.recall_steps
    assert run.write_steps
