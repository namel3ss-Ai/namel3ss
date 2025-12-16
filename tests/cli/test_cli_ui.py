import json

from namel3ss.cli.main import main


SOURCE = '''record "Item":
  name string

flow "demo":
  return "ok"

page "home":
  button "Run":
    calls flow "demo"
'''


def test_ui_manifest(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path), "ui"])
    out = capsys.readouterr().out
    assert code == 0
    manifest = json.loads(out)
    assert "pages" in manifest
    assert "actions" in manifest
    assert "page.home.button.run" in manifest["actions"]
