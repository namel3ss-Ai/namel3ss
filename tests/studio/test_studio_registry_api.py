from __future__ import annotations

import zipfile
from pathlib import Path

from namel3ss.runtime.packs.trust_store import TrustedKey, add_trusted_key
from namel3ss.studio import registry_api


FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "registry" / "bundles"


def test_studio_registry_api_flow(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('flow "demo":\n  return "ok"\n', encoding="utf-8")
    bundle_path = FIXTURES_ROOT / "sample.local-0.1.0.n3pack.zip"
    digest = _signature_from_bundle(bundle_path)
    add_trusted_key(tmp_path, TrustedKey(key_id="test.key", public_key=digest))

    status = registry_api.get_registry_status_payload(str(app_path))
    assert status["ok"] is True
    assert any(source["kind"] == "local_index" for source in status["sources"])

    add_payload = registry_api.apply_registry_add_bundle(str(app_path), {"path": str(bundle_path)})
    assert add_payload["ok"] is True

    discover = registry_api.apply_discover(str(app_path), {"phrase": "provide"})
    assert discover["ok"] is True
    assert discover["count"] >= 1

    install = registry_api.apply_pack_install(str(app_path), {"pack_id": "sample.local", "pack_version": "0.1.0"})
    assert install["ok"] is True
    assert (tmp_path / ".namel3ss" / "packs" / "sample.local" / "pack.yaml").exists()


def _signature_from_bundle(path: Path) -> str:
    with zipfile.ZipFile(path, "r") as archive:
        data = archive.read("signature.txt")
    return data.decode("utf-8").strip()
