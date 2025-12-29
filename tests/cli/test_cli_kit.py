import json
import os
from pathlib import Path

from namel3ss.cli.main import main
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME


def _write_project(root: Path) -> None:
    (root / "packages").mkdir()
    (root / LOCKFILE_FILENAME).write_text('{"lockfile_version":1,"roots":[],"packages":[]}', encoding="utf-8")
    (root / "app.ai").write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    kit_state = root / ".namel3ss"
    kit_state.mkdir(parents=True)
    (kit_state / "verify.json").write_text(json.dumps({"status": "ok", "checks": []}), encoding="utf-8")


def test_cli_kit_generates_markdown(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["kit", "--format", "md"])
    assert code == 0
    output = capsys.readouterr().out
    assert "Kit written to" in output
    kit_path = tmp_path / ".namel3ss" / "kit" / "adoption.md"
    content = kit_path.read_text(encoding="utf-8")
    assert "# Adoption kit" in content
    assert "## Trust posture" in content


def test_cli_kit_redacts_urls(tmp_path: Path, monkeypatch) -> None:
    _write_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("N3_PERSIST_TARGET", "postgres")
    monkeypatch.setenv("N3_DATABASE_URL", "postgres://user:secret@host/db")
    main(["kit", "--format", "md"])
    content = (tmp_path / ".namel3ss" / "kit" / "adoption.md").read_text(encoding="utf-8")
    assert "postgres://user:secret@host/db" not in content
