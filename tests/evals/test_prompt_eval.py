from __future__ import annotations

import json
from pathlib import Path

from namel3ss.evals.prompt_eval import run_prompt_eval


def test_prompt_eval_writes_results(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("N3_PERSIST_ROOT", str(tmp_path))
    app_path = tmp_path / "app.ai"
    app_path.write_text(
        '\n'.join(
            [
                'spec is "1.0"',
                '',
                'prompt "summary_prompt":',
                '  version is "1.0.0"',
                '  text is "Summarise."',
            ]
        ),
        encoding="utf-8",
    )
    input_path = tmp_path / "inputs.json"
    expected_output = "[mock-model] Summarise. :: hello"
    input_path.write_text(json.dumps({"input": "hello", "expected": expected_output}), encoding="utf-8")
    payload = run_prompt_eval(
        prompt_name="summary_prompt",
        input_path=input_path,
        app_path=Path(app_path),
        out_dir=None,
    )
    assert payload["summary"] == {"accuracy": 1.0, "similarity": 1.0, "cases": 1}
    eval_path = tmp_path / ".namel3ss" / "observability" / "evals" / "summary_prompt" / "prompt_eval.json"
    assert eval_path.exists()
    stored = json.loads(eval_path.read_text(encoding="utf-8"))
    assert stored == payload
