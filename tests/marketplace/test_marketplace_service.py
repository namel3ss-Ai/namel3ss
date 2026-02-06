from __future__ import annotations

from pathlib import Path

from namel3ss.marketplace import approve_item, install_item, item_comments, publish_item, rate_item, search_items
from namel3ss.utils.simple_yaml import parse_yaml



def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app



def _write_item(tmp_path: Path) -> Path:
    item_root = tmp_path / "item"
    item_root.mkdir(parents=True, exist_ok=True)
    (item_root / "market_flow.ai").write_text('flow "market_demo":\n  return "ok"\n', encoding="utf-8")
    (item_root / "manifest.yaml").write_text(
        "name: demo.flow\n"
        "version: 0.1.0\n"
        "type: flow\n"
        "description: Demo marketplace flow\n"
        "author: test\n"
        "license: MIT\n"
        "files:\n"
        "  - market_flow.ai\n",
        encoding="utf-8",
    )
    return item_root



def test_marketplace_publish_search_install_and_rate(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    item_root = _write_item(tmp_path)

    first = publish_item(project_root=app.parent, app_path=app, item_path=item_root)
    second = publish_item(project_root=app.parent, app_path=app, item_path=item_root)
    assert first["digest"] == second["digest"]
    assert first["status"] == "pending_review"

    approve_item(project_root=app.parent, app_path=app, name="demo.flow", version="0.1.0")

    items = search_items(project_root=app.parent, app_path=app, query="demo.flow", include_pending=False)
    assert len(items) == 1
    assert items[0]["name"] == "demo.flow"

    installed = install_item(project_root=app.parent, app_path=app, name="demo.flow", version="0.1.0")
    assert installed["ok"] is True
    installed_files = installed["installed_files"]
    assert any(path.endswith("market_flow.ai") for path in installed_files)
    capabilities_path = Path(str(installed["capabilities_path"]))
    assert capabilities_path.exists()
    parsed = parse_yaml(capabilities_path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    entries = parsed.get("marketplace_items")
    assert isinstance(entries, list)
    assert entries[0]["name"] == "demo.flow"

    rate_item(project_root=app.parent, app_path=app, name="demo.flow", version="0.1.0", rating=5, comment="useful")
    comments = item_comments(project_root=app.parent, app_path=app, name="demo.flow", version="0.1.0")
    assert comments
    assert comments[0]["rating"] == 5


def test_marketplace_supports_capability_yaml_manifest(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    item_root = tmp_path / "item_capability"
    item_root.mkdir(parents=True, exist_ok=True)
    (item_root / "market_flow.ai").write_text('flow "market_demo":\n  return "ok"\n', encoding="utf-8")
    (item_root / "capability.yaml").write_text(
        "name: demo.capability\n"
        "version: 0.2.0\n"
        "type: flow\n"
        "description: Demo capability manifest\n"
        "author: test\n"
        "license: MIT\n"
        "files:\n"
        "  - market_flow.ai\n"
        "requirements:\n"
        "  - requests==2.31.0\n",
        encoding="utf-8",
    )

    published = publish_item(project_root=app.parent, app_path=app, item_path=item_root)
    assert published["ok"] is True
    approve_item(project_root=app.parent, app_path=app, name="demo.capability", version="0.2.0")

    items = search_items(project_root=app.parent, app_path=app, query="demo.capability", include_pending=False)
    assert len(items) == 1
    dependencies = items[0].get("dependencies")
    assert isinstance(dependencies, list)
    assert dependencies == ["requests==2.31.0"]
