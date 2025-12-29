from __future__ import annotations

import shutil
from pathlib import Path

from namel3ss.runtime.packs.manifest import parse_pack_manifest
from namel3ss.studio import api


def test_studio_packs_payload_includes_pack(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "packs" / "pack_good_unverified"
    manifest = parse_pack_manifest(fixture_root / "pack.yaml")
    pack_dest = tmp_path / ".namel3ss" / "packs" / manifest.pack_id
    shutil.copytree(fixture_root, pack_dest)
    payload = api.get_packs_payload(str(app_path))
    assert payload["ok"] is True
    pack_ids = [pack["pack_id"] for pack in payload["packs"]]
    assert manifest.pack_id in pack_ids
    pack = next(item for item in payload["packs"] if item["pack_id"] == manifest.pack_id)
    assert pack["verified"] is False
