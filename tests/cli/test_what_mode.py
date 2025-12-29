from __future__ import annotations

from pathlib import Path

from namel3ss.cli.main import main as cli_main
from namel3ss.outcome.builder import build_outcome_pack
from namel3ss.outcome.model import MemoryOutcome, StateOutcome, StoreOutcome


def test_what_missing_artifacts(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli_main(["what"])
    out = capsys.readouterr().out
    assert rc != 0
    assert "No run outcome recorded yet" in out


def test_what_reads_plain(tmp_path: Path, monkeypatch, capsys) -> None:
    outcome_dir = tmp_path / ".namel3ss" / "outcome"
    outcome_dir.mkdir(parents=True)
    (outcome_dir / "last.json").write_text("{}\n", encoding="utf-8")
    (outcome_dir / "last.plain").write_text("plain outcome\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    rc = cli_main(["what"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.strip() == "plain outcome"


def test_what_renders_from_json(tmp_path: Path, monkeypatch, capsys) -> None:
    store = StoreOutcome(began=True, committed=True, commit_failed=False, rolled_back=False, rollback_failed=False)
    state = StateOutcome(loaded_from_store=False, save_attempted=True, save_succeeded=True, save_failed=False)
    memory = MemoryOutcome(persist_attempted=True, persist_succeeded=True, persist_failed=False, skipped_reason=None)
    build_outcome_pack(
        flow_name="demo",
        store=store,
        state=state,
        memory=memory,
        record_changes_count=0,
        execution_steps_count=0,
        traces_count=0,
        error_escaped=False,
        project_root=tmp_path,
    )
    outcome_dir = tmp_path / ".namel3ss" / "outcome"
    (outcome_dir / "last.plain").unlink()

    monkeypatch.chdir(tmp_path)
    rc = cli_main(["what"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "run outcome" in out.lower()
