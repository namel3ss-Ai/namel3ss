from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    module_path = Path("scripts/convert_state_to_training_dataset.py").resolve()
    spec = importlib.util.spec_from_file_location("convert_state_to_training_dataset", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_convert_state_file_and_check_mode(tmp_path: Path) -> None:
    module = _load_module()
    input_path = tmp_path / "state.json"
    output_path = tmp_path / "dataset.jsonl"
    input_path.write_text(
        json.dumps(
            {
                "records": [
                    {"input": "q1", "target": "a1"},
                    {"input": "q2", "target": "a2"},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert module.main(["--input", str(input_path), "--output", str(output_path)]) == 0
    assert output_path.exists()

    assert module.main(["--input", str(input_path), "--output", str(output_path), "--check"]) == 0

    output_path.write_text("{}\n", encoding="utf-8")
    assert module.main(["--input", str(input_path), "--output", str(output_path), "--check"]) == 1


def test_convert_state_file_fails_for_missing_input(tmp_path: Path) -> None:
    module = _load_module()
    input_path = tmp_path / "missing.json"
    output_path = tmp_path / "dataset.jsonl"

    assert module.main(["--input", str(input_path), "--output", str(output_path)]) == 1
