from __future__ import annotations

import hashlib
import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"

page "home":
  button "Run":
    calls flow "demo"
'''


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_ui_bundle_writes_deterministic_assets(tmp_path: Path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    out_dir = tmp_path / "dist" / "ui"

    code = cli_main([str(app_path), "ui", "bundle", "--out", out_dir.as_posix()])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True

    manifest_path = out_dir / "bundle_manifest.json"
    index_path = out_dir / "index.html"
    runtime_js = out_dir / "runtime.js"
    runtime_css = out_dir / "runtime.css"
    ui_manifest = out_dir / "ui_manifest.json"
    ui_actions = out_dir / "ui_actions.json"
    ui_state = out_dir / "ui_state.json"

    for path in [manifest_path, index_path, runtime_js, runtime_css, ui_manifest, ui_actions, ui_state]:
        assert path.exists()

    first_hash = _sha256(manifest_path)

    code_two = cli_main([str(app_path), "ui", "bundle", "--out", out_dir.as_posix()])
    out_two = capsys.readouterr().out
    assert code_two == 0
    payload_two = json.loads(out_two)
    assert payload_two["ok"] is True

    second_hash = _sha256(manifest_path)
    assert first_hash == second_hash
