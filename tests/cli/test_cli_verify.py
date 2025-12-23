import json

from namel3ss.cli.main import main
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME


BASE_SOURCE = '''record "Item":
  field "name" is text

flow "demo":
  return "ok"
'''


MUTATING_SOURCE = '''record "Item":
  field "name" is text

flow "seed":
  save Item
'''


def _write_app(tmp_path, source):
    path = tmp_path / "app.ai"
    path.write_text(source, encoding="utf-8")


def _write_lock(tmp_path):
    lock_path = tmp_path / LOCKFILE_FILENAME
    lock_path.write_text('{"lockfile_version":1,"roots":[],"packages":[]}', encoding="utf-8")


def _prepare_packages(tmp_path):
    (tmp_path / "packages").mkdir()


def test_verify_ok_json(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path, BASE_SOURCE)
    _write_lock(tmp_path)
    _prepare_packages(tmp_path)
    monkeypatch.chdir(tmp_path)
    main(["pack", "--target", "local"])
    capsys.readouterr()
    code = main(["verify", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["status"] == "ok"
    assert payload["schema_version"] == 1


def test_verify_prod_fails_on_public_mutation(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path, MUTATING_SOURCE)
    _write_lock(tmp_path)
    _prepare_packages(tmp_path)
    monkeypatch.chdir(tmp_path)
    main(["pack", "--target", "local"])
    capsys.readouterr()
    code = main(["verify", "--prod", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["status"] == "fail"
