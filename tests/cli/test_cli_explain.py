import json

from namel3ss.cli.main import main
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME


APP_SOURCE = '''flow "demo":
  return "ok"
'''


def _write_app(tmp_path):
    path = tmp_path / "app.ai"
    path.write_text(APP_SOURCE, encoding="utf-8")


def _write_lock(tmp_path):
    lock_path = tmp_path / LOCKFILE_FILENAME
    lock_path.write_text('{"lockfile_version":1,"roots":[],"packages":[]}', encoding="utf-8")


def test_explain_references_active_proof(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    _write_lock(tmp_path)
    (tmp_path / "packages").mkdir()
    monkeypatch.chdir(tmp_path)
    main(["pack", "--target", "service"])
    main(["ship", "--to", "service"])
    capsys.readouterr()
    code = main(["explain", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["active_proof_id"]
