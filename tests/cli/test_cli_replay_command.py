from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main
from namel3ss.runtime.explainability.logger import explain_replay_hash


def _write_app(tmp_path: Path) -> None:
    (tmp_path / "app.ai").write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")


def _write_explain_log(tmp_path: Path, *, valid_hash: bool) -> Path:
    entries = [
        {
            "event_index": 1,
            "timestamp": "1970-01-01T00:00:00.001Z",
            "stage": "generation",
            "event_type": "start",
            "seed": 42,
            "provider": "mock",
            "model": "mock-model",
            "metadata": {},
        },
        {
            "event_index": 2,
            "timestamp": "1970-01-01T00:00:00.002Z",
            "stage": "retrieval",
            "event_type": "selected_chunks",
            "seed": 42,
            "provider": "",
            "model": "",
            "metadata": {
                "modality": "image",
                "selected": [
                    {
                        "doc_id": "doc-image",
                        "chunk_id": "doc-image:0",
                        "page_number": 1,
                        "score": 3,
                        "source_url": "image.png",
                        "modality": "image",
                    }
                ],
            },
        },
    ]
    replay_hash = explain_replay_hash(entries) if valid_hash else "invalid"
    payload = {
        "schema_version": 1,
        "flow_name": "demo",
        "entry_count": len(entries),
        "generated_at": "1970-01-01T00:00:00.002Z",
        "replay_hash": replay_hash,
        "entries": entries,
    }
    path = tmp_path / ".namel3ss" / "explain" / "last_explain.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_replay_command_reads_log_and_returns_seed_and_retrieval_metadata(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    _write_app(tmp_path)
    _write_explain_log(tmp_path, valid_hash=True)
    monkeypatch.chdir(tmp_path)

    assert cli_main(["replay", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["hash_verified"] is True
    assert payload["seeds"] == [42]
    assert payload["retrieval_events"][0]["modality"] == "image"
    assert payload["retrieval_events"][0]["selected"][0]["chunk_id"] == "doc-image:0"


def test_replay_command_fails_when_replay_hash_is_invalid(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    _write_explain_log(tmp_path, valid_hash=False)
    monkeypatch.chdir(tmp_path)

    assert cli_main(["replay", "--json"]) == 1
    error = capsys.readouterr().err
    assert "Replay hash validation failed" in error


def test_replay_command_can_skip_hash_verification_with_explicit_log(
    tmp_path: Path, capsys
) -> None:
    log_path = _write_explain_log(tmp_path, valid_hash=False)

    assert cli_main(["replay", "--log", str(log_path), "--no-verify", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["hash_verified"] is False

