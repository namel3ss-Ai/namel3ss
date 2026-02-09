from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main
from namel3ss.determinism import canonical_json_dumps
from namel3ss.tools.app_archive import read_archive, write_archive


APP_SOURCE = '''spec is "1.0"

capabilities:
  app_packaging
  app_permissions

permissions:
  ai:
    call: denied
    tools: denied
  uploads:
    read: denied
    write: denied
  ui_state:
    persistent_write: denied
  navigation:
    change_page: denied

flow "demo":
  return "ok"

page "Home":
  text is "Ready"
'''


def _build_archive(tmp_path: Path, capsys) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    assert main(["build", app_path.as_posix()]) == 0
    out = capsys.readouterr().out.strip()
    return Path(out)


def test_run_archive_defaults_to_production(tmp_path: Path, capsys) -> None:
    archive = _build_archive(tmp_path, capsys)

    code = main(["run", archive.as_posix()])
    out = capsys.readouterr().out

    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["mode"] == "production"


def test_run_archive_studio_mode(tmp_path: Path, capsys) -> None:
    archive = _build_archive(tmp_path, capsys)

    code = main(["run", archive.as_posix(), "studio"])
    out = capsys.readouterr().out

    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["mode"] == "studio"


def test_run_rejects_invalid_archive_file(tmp_path: Path, capsys) -> None:
    archive = tmp_path / "broken.n3a"
    archive.write_text("not-a-zip", encoding="utf-8")

    code = main(["run", archive.as_posix()])
    err = capsys.readouterr().err

    assert code == 1
    assert "This file is not a namel3ss app." in err


def test_run_rejects_missing_permission_declaration(tmp_path: Path, capsys) -> None:
    archive = _build_archive(tmp_path, capsys)
    entries = read_archive(archive)
    permissions = json.loads(entries["permissions.json"].decode("utf-8"))
    permissions.pop("uploads.read", None)
    entries["permissions.json"] = canonical_json_dumps(
        permissions,
        pretty=True,
        drop_run_keys=False,
    ).encode("utf-8")
    patched = tmp_path / "patched.n3a"
    write_archive(patched, entries)

    code = main(["run", patched.as_posix()])
    err = capsys.readouterr().err

    assert code == 1
    assert "This app asks for permissions it does not declare." in err
