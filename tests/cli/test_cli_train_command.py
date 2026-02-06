from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


def _write_app(tmp_path: Path, *, include_training_capability: bool) -> None:
    capabilities = "\ncapabilities:\n  training\n" if include_training_capability else ""
    (tmp_path / "app.ai").write_text(
        f'spec is "1.0"\n{capabilities}\nflow "demo":\n  return "ok"\n',
        encoding="utf-8",
    )


def _write_dataset(tmp_path: Path) -> Path:
    path = tmp_path / "data" / "train.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '\n'.join(
            [
                '{"input":"q1","target":"a1"}',
                '{"input":"q2","target":"a2"}',
                '{"input":"q3","target":"a3"}',
            ]
        )
        + '\n',
        encoding="utf-8",
    )
    return path


def test_train_command_requires_training_capability(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path, include_training_capability=False)
    _write_dataset(tmp_path)
    monkeypatch.chdir(tmp_path)

    code = cli_main(
        [
            "train",
            "--model-base",
            "gpt-3.5-turbo",
            "--dataset",
            "data/train.jsonl",
            "--output-name",
            "supportbot.faq_model_v1",
            "--json",
        ]
    )
    assert code == 1
    err = capsys.readouterr().err
    assert "training" in err


def test_train_command_runs_and_registers_model(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path, include_training_capability=True)
    _write_dataset(tmp_path)
    monkeypatch.chdir(tmp_path)

    command = [
        "train",
        "--model-base",
        "gpt-3.5-turbo",
        "--dataset",
        "data/train.jsonl",
        "--epochs",
        "2",
        "--learning-rate",
        "2e-5",
        "--seed",
        "11",
        "--output-name",
        "supportbot.faq_model_v2",
        "--json",
    ]

    assert cli_main(command) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["model_name"] == "supportbot.faq_model_v2"
    assert payload["model_ref"] == "supportbot.faq_model_v2@2.0.0"
    assert set(payload["metrics"].keys()) == {"accuracy", "bleu"}

    assert cli_main(command) == 1
    err = capsys.readouterr().err
    assert "already exists" in err


def test_train_command_reports_missing_required_fields(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path, include_training_capability=True)
    monkeypatch.chdir(tmp_path)

    assert cli_main(["train", "--json"]) == 1
    err = capsys.readouterr().err
    assert "model_base" in err
