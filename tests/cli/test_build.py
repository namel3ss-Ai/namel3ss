from __future__ import annotations

from pathlib import Path

from namel3ss.cli.main import main


APP_SOURCE = '''spec is "1.0"

capabilities:
  app_packaging
  app_permissions
  ui_state

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

ui_state:
  session:
    current_page is text

flow "demo":
  return "ok"

page "Home":
  text is "Ready"
'''


def test_build_writes_n3a_next_to_source(tmp_path: Path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")

    code = main(["build", app_path.as_posix()])
    out = capsys.readouterr().out.strip()

    assert code == 0
    archive_path = Path(out)
    assert archive_path.exists()
    assert archive_path.name == "app.n3a"


def test_build_out_path_is_supported(tmp_path: Path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    out_path = tmp_path / "dist" / "custom.n3a"

    code = main(["build", app_path.as_posix(), "--out", out_path.as_posix()])
    out = capsys.readouterr().out.strip()

    assert code == 0
    assert Path(out) == out_path
    assert out_path.exists()


def test_build_requires_packaging_capability(tmp_path: Path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(
        'spec is "1.0"\n\nflow "demo":\n  return "ok"\n',
        encoding="utf-8",
    )

    code = main(["build", app_path.as_posix()])
    err = capsys.readouterr().err

    assert code == 1
    assert "Capability \"app_packaging\" is required." in err
