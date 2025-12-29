import json

from namel3ss.cli.main import main
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME


APP_SOURCE = '''record "Item":
  field "name" is text

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
    lock_path.write_text('{"lockfile_version":1,"roots":[],"packages":[]}', encoding="utf-8")


def test_proof_writes_file_and_is_stable(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    _write_lock(tmp_path)
    (tmp_path / "packages").mkdir()
    monkeypatch.chdir(tmp_path)
    code = main(["proof", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    proof_id = payload["proof_id"]
    proof_path = tmp_path / ".namel3ss" / "proofs" / f"{proof_id}.json"
    assert proof_path.exists()

    code = main(["proof", "--json"])
    out2 = capsys.readouterr().out
    payload2 = json.loads(out2)
    assert code == 0
    assert payload2["proof_id"] == proof_id
