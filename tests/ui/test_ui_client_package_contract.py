from __future__ import annotations

import json
from pathlib import Path


def test_ui_client_package_contract_files_exist() -> None:
    package_json = Path("packages/namel3ss-ui-client/package.json")
    entry = Path("packages/namel3ss-ui-client/src/index.js")

    assert package_json.exists()
    assert entry.exists()

    payload = json.loads(package_json.read_text(encoding="utf-8"))
    assert payload["name"] == "@namel3ss/ui-client"
    assert payload["main"] == "src/index.js"

    source = entry.read_text(encoding="utf-8")
    for token in [
        "getManifest",
        "getState",
        "getActions",
        "runAction",
        "/api/v1/ui",
        "/api/v1/actions/",
        "/api/ui/manifest",
        "/api/ui/action",
        "X-API-Token",
    ]:
        assert token in source
