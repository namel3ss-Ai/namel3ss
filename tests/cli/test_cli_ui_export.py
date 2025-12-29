import json
from pathlib import Path

from namel3ss.cli.main import main


SOURCE = '''spec is "1.0"

record "User":
  name text

flow "demo":
  return "ok"

page "Home":
  form is "User"
  button "Run":
    calls flow "demo"
'''


def test_cli_ui_export_writes_files(tmp_path: Path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    code = main([str(app_path), "ui", "export"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    export_dir = Path(payload["export_dir"])
    assert export_dir.exists()
    assert (export_dir / "ui.json").exists()
    assert (export_dir / "actions.json").exists()
    assert (export_dir / "schema.json").exists()
