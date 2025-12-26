from pathlib import Path

from namel3ss.pkg.lockfile import LOCKFILE_FILENAME
from namel3ss.studio import graph_api


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_graph_and_exports_payloads(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(
        'use "local" as local\nuse "shared" as shared\n\nflow "demo":\n  return "ok"\n',
        encoding="utf-8",
    )
    _write_file(
        tmp_path / "modules" / "local" / "capsule.ai",
        'capsule "local":\n  exports:\n    flow "local_flow"\n',
    )
    _write_file(
        tmp_path / "modules" / "local" / "logic.ai",
        'flow "local_flow":\n  return "local"\n',
    )
    _write_file(
        tmp_path / "packages" / "shared" / "capsule.ai",
        'capsule "shared":\n  exports:\n    flow "shared_flow"\n',
    )
    _write_file(
        tmp_path / "packages" / "shared" / "logic.ai",
        'flow "shared_flow":\n  return "shared"\n',
    )
    (tmp_path / LOCKFILE_FILENAME).write_text(
        "".join([
            "{\n",
            "  \"lockfile_version\": 1,\n",
            "  \"roots\": [{\"name\": \"shared\", \"source\": \"github:owner/shared@v0.1.0\"}],\n",
            "  \"packages\": [{\n",
            "    \"name\": \"shared\",\n",
            "    \"version\": \"0.1.0\",\n",
            "    \"source\": \"github:owner/shared@v0.1.0\",\n",
            "    \"checksums\": [],\n",
            "    \"dependencies\": [],\n",
            "    \"license\": \"MIT\"\n",
            "  }]\n",
            "}\n",
        ]),
        encoding="utf-8",
    )

    graph = graph_api.get_graph_payload(str(app_path))
    assert graph["schema_version"] == 1
    node_ids = [node["id"] for node in graph["nodes"]]
    assert node_ids == sorted(node_ids)
    assert "app" in node_ids
    assert "capsule:local" in node_ids
    assert "package:shared" in node_ids
    edges = graph["edges"]
    assert edges == sorted(edges, key=lambda item: (item.get("from", ""), item.get("to", "")))
    assert {"from": "app", "to": "capsule:local"} in edges
    assert {"from": "app", "to": "package:shared"} in edges

    exports = graph_api.get_exports_payload(str(app_path))
    assert exports["schema_version"] == 1
    capsule_names = [capsule["name"] for capsule in exports["capsules"]]
    assert capsule_names == sorted(capsule_names)
    shared = next(c for c in exports["capsules"] if c["name"] == "shared")
    assert shared["type"] == "package"
    assert shared["version"] == "0.1.0"
