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


def test_run_command_local_default(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["run", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["ok"] is True
    assert payload["result"] == "ok"


def test_pack_creates_artifacts_for_service_target(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    lock_path = tmp_path / LOCKFILE_FILENAME
    lock_path.write_text('{"lockfile_version":1,"roots":[],"packages":[]}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    code = main(["pack", "--target", "service"])
    assert code == 0
    capsys.readouterr()
    latest_path = tmp_path / ".namel3ss" / "build" / "service" / "latest.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    build_id = latest["build_id"]
    build_dir = tmp_path / ".namel3ss" / "build" / "service" / build_id
    assert (build_dir / "build.json").exists()
    assert (build_dir / "program" / "app.ai").exists()
    meta = json.loads((build_dir / "build.json").read_text(encoding="utf-8"))
    assert meta["target"] == "service"
    assert meta["recommended_persistence"] == "postgres"
    lock_snapshot = json.loads((build_dir / "lock_snapshot.json").read_text(encoding="utf-8"))
    assert lock_snapshot["status"] == "present"
    program_copy = (build_dir / "program" / "app.ai").read_text(encoding="utf-8")
    assert "flow \"demo\"" in program_copy


def test_ship_where_and_back(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    main(["pack", "--target", "service"])
    latest_path = tmp_path / ".namel3ss" / "build" / "service" / "latest.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    build_id = latest["build_id"]

    code = main(["ship", "--to", "service"])
    assert code == 0
    state = json.loads((tmp_path / ".namel3ss" / "promotion.json").read_text(encoding="utf-8"))
    assert state["active"]["target"] == "service"
    assert state["active"]["build_id"] == build_id
    active_proof = json.loads((tmp_path / ".namel3ss" / "active_proof.json").read_text(encoding="utf-8"))
    assert active_proof["target"] == "service"
    assert active_proof["build_id"] == build_id
    assert active_proof["proof_id"]

    code = main(["where"])
    out = capsys.readouterr().out.lower()
    assert code == 0
    assert "active target: service" in out
    assert build_id.lower() in out

    code = main(["ship", "--back"])
    out = capsys.readouterr().out.lower()
    state_after = json.loads((tmp_path / ".namel3ss" / "promotion.json").read_text(encoding="utf-8"))
    assert code == 0
    assert state_after["active"]["target"] is None
    assert "rolled back" in out
    active_after = json.loads((tmp_path / ".namel3ss" / "active_proof.json").read_text(encoding="utf-8"))
    assert active_after.get("proof_id") in {None, ""}


def test_status_reports_artifacts_after_promote(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    main(["build", "--target", "service"])
    latest_path = tmp_path / ".namel3ss" / "build" / "service" / "latest.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    build_id = latest["build_id"]

    code = main(["promote", "--to", "service"])
    assert code == 0
    state = json.loads((tmp_path / ".namel3ss" / "promotion.json").read_text(encoding="utf-8"))
    assert state["active"]["build_id"] == build_id

    code = main(["status"])
    out = capsys.readouterr().out.lower()
    assert code == 0
    assert "artifacts present: yes" in out
    assert ".namel3ss" in out
