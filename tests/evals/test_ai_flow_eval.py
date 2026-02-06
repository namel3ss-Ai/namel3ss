from __future__ import annotations

import json
from pathlib import Path

from namel3ss.evals.ai_flow_eval import AI_EVAL_FILENAME, run_ai_flow_eval


def test_run_ai_flow_eval_writes_deterministic_payload(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    app.write_text(
        '''
spec is "1.0"

qa "answer_question":
  model is "gpt-4"
  prompt is "Qn: " + input.question + "\\nCtx: " + input.context + "\\nAns: "
  output:
    ans is text
  tests:
    dataset is "qa_examples.json"
    metrics:
      - accuracy
      - exact_match
'''.lstrip(),
        encoding="utf-8",
    )
    dataset = tmp_path / "qa_examples.json"
    dataset.write_text(
        json.dumps(
            [
                {
                    "input": {"question": "Hi", "context": "World"},
                    "expected": '[gpt-4] Qn: Hi\nCtx: World\nAns:  :: {"context":"World","question":"Hi"}',
                }
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    payload = run_ai_flow_eval(flow_name="answer_question", app_path=app, out_dir=out_dir)
    assert payload["flow_name"] == "answer_question"
    assert payload["results"]["accuracy"] == 1.0
    assert payload["results"]["exact_match"] == 1.0
    assert (out_dir / AI_EVAL_FILENAME).exists()
