from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


def test_cli_eval_flow_command(tmp_path: Path, capsys, monkeypatch) -> None:
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
'''.lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "qa_examples.json").write_text(
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
    monkeypatch.chdir(tmp_path)
    assert cli_main(["eval", "flow", "answer_question", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["flow_name"] == "answer_question"
    assert payload["results"]["accuracy"] == 1.0
