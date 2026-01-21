from __future__ import annotations

from pathlib import Path

from namel3ss.beta_lock.repo_clean import repo_dirty_entries
from namel3ss.cli.main import main as cli_main


def test_registry_commands_keep_repo_clean(tmp_path: Path, capsys, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[2]
    baseline = set(repo_dirty_entries(root))
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert cli_main(["registry", "list", "--json"]) == 0
    capsys.readouterr()
    dirty = set(repo_dirty_entries(root))
    assert dirty == baseline


def _write_app(tmp_path: Path) -> None:
    (tmp_path / "app.ai").write_text('flow "demo":\n  return "ok"\n', encoding="utf-8")
