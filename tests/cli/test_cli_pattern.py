import json
from pathlib import Path

from namel3ss.cli.main import main
from namel3ss.patterns.index import PATTERN_PATH_ENV


def test_cli_pattern_list_json(monkeypatch, capsys):
    patterns_path = Path("patterns").resolve()
    monkeypatch.setenv(PATTERN_PATH_ENV, str(patterns_path))
    code = main(["pattern", "list", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["schema_version"] == 1
    assert payload["count"] >= 5


def test_cli_pattern_new(monkeypatch, tmp_path):
    patterns_path = Path("patterns").resolve()
    monkeypatch.setenv(PATTERN_PATH_ENV, str(patterns_path))
    monkeypatch.chdir(tmp_path)
    code = main(["pattern", "new", "admin-dashboard", "my_admin"])
    assert code == 0
    assert (tmp_path / "my_admin" / "app.ai").exists()
