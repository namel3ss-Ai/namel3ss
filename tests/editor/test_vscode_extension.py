from __future__ import annotations

import json
from pathlib import Path


def test_vscode_extension_manifest() -> None:
    root = Path(__file__).resolve().parents[2]
    manifest = root / "extensions" / "vscode" / "package.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["name"] == "namel3ss-editor"
    languages = data.get("contributes", {}).get("languages", [])
    assert any(lang.get("id") == "namel3ss" for lang in languages)
    assert data.get("main") == "./extension.js"
