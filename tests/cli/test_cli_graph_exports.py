import json
from pathlib import Path

from namel3ss.cli.main import main


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_cli_graph_and_exports_json(tmp_path, capsys):
    app = tmp_path / "app.ai"
    _write(app, 'use "inventory" as inv\nspec is "1.0"\n\nflow "demo":\n  return "ok"\n')
    _write(
        tmp_path / "modules" / "inventory" / "capsule.ai",
        'capsule "inventory":\n'
        "  exports:\n"
        '    flow "calc_total"\n',
    )
    _write(
        tmp_path / "modules" / "inventory" / "logic.ai",
        'flow "calc_total":\n'
        "  return 42\n",
    )

    code = main([str(app), "graph", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert "(app)" in payload["nodes"]
    assert {"from": "(app)", "to": "inventory"} in payload["edges"]

    code = main([str(app), "exports", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["modules"][0]["name"] == "inventory"
    assert "flow" in payload["modules"][0]["exports"]
