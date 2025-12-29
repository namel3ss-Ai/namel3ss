from pathlib import Path
import json

from namel3ss.module_loader import load_project
from namel3ss.runtime.executor.api import execute_program_flow


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_module_trace_goldens(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    module_path = tmp_path / "modules" / "common.ai"
    _write(
        module_path,
        (
            'define function "value":\n'
            '  input:\n'
            '    x is number\n'
            '  return 2\n'
        ),
    )
    _write(
        app_path,
        (
            'spec is "1.0"\n\n'
            'define function "value":\n'
            '  input:\n'
            '    x is number\n'
            '  return 1\n\n'
            'use module "modules/common.ai" as common\n'
            'allow override:\n'
            '  functions\n\n'
            'flow "demo":\n'
            '  return call function "value":\n'
            '    x is 1\n'
        ),
    )
    project = load_project(app_path)
    result = execute_program_flow(project.program, "demo", state={}, input={})
    events = [
        trace
        for trace in result.traces
        if isinstance(trace, dict) and trace.get("type") in {"module_loaded", "module_merged", "module_overrides"}
    ]
    by_type = {event["type"]: event for event in events}
    golden_dir = Path("tests/golden/phase3/traces")
    for event_type in ("module_loaded", "module_merged", "module_overrides"):
        expected = json.loads((golden_dir / f"{event_type}.json").read_text(encoding="utf-8"))
        assert by_type[event_type] == expected
