import json

from namel3ss.cli.main import main
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME


APP_SOURCE = '''record "Item":
  name text

spec is "1.0"

flow "demo":
  return "ok"
'''


def _write_app(tmp_path):
    path = tmp_path / "app.ai"
    path.write_text(APP_SOURCE, encoding="utf-8")
    return path


def _write_lock(tmp_path):
    lock_path = tmp_path / LOCKFILE_FILENAME
    lock_path.write_text(json.dumps({"lockfile_version": 1, "roots": [], "packages": []}), encoding="utf-8")


def test_ship_blocks_pending_migrations(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    _write_lock(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["pack", "--target", "service"])
    assert code == 0
    capsys.readouterr()
    code = main(["migrate", "plan"])
    assert code == 0
    capsys.readouterr()
    code = main(["ship", "--to", "service"])
    assert code == 1
    err = capsys.readouterr().err.lower()
    assert "pending migrations" in err
