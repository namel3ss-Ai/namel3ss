from __future__ import annotations

import json
import shutil
from pathlib import Path

from namel3ss.module_loader import load_project
from namel3ss.config.model import ToolPacksConfig
from namel3ss.runtime.packs.config import write_pack_config
from namel3ss.runtime.packs.manifest import parse_pack_manifest
from namel3ss.runtime.packs.verification import compute_pack_digest
from namel3ss.tools.health.analyze import analyze_tool_health


TOOL_SOURCE = '''tool "greeter":
  implemented using python

  input:
    name is text

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  return "ok"
'''


def _write_app(tmp_path: Path) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(TOOL_SOURCE, encoding="utf-8")
    return app_path


def test_health_service_runner_missing_url(tmp_path: Path, monkeypatch) -> None:
    app_path = _write_app(tmp_path)
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n  "greeter":\n    kind: "python"\n    entry: "tools.greeter:run"\n    runner: "service"\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("N3_TOOL_SERVICE_URL", raising=False)
    project = load_project(app_path)
    report = analyze_tool_health(project)
    assert "greeter" in report.service_missing_urls
    assert any(issue.code == "tools.service_url_missing" for issue in report.issues)


def test_health_container_runner_missing_image(tmp_path: Path, monkeypatch) -> None:
    app_path = _write_app(tmp_path)
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n  "greeter":\n    kind: "python"\n    entry: "tools.greeter:run"\n    runner: "container"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("namel3ss.tools.health.analyze.detect_container_runtime", lambda: "docker")
    project = load_project(app_path)
    report = analyze_tool_health(project)
    assert "greeter" in report.container_missing_images
    assert "greeter" not in report.container_missing_runtime


def test_health_container_runner_missing_runtime(tmp_path: Path, monkeypatch) -> None:
    app_path = _write_app(tmp_path)
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n'
        '  "greeter":\n'
        '    kind: "python"\n'
        '    entry: "tools.greeter:run"\n'
        '    runner: "container"\n'
        '    image: "ghcr.io/namel3ss/tools:latest"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("namel3ss.tools.health.analyze.detect_container_runtime", lambda: None)
    project = load_project(app_path)
    report = analyze_tool_health(project)
    assert "greeter" in report.container_missing_runtime


def test_health_pack_collisions(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    pack_a = _install_pack(tmp_path, "pack_collision_a")
    pack_b = _install_pack(tmp_path, "pack_collision_b")
    write_pack_config(
        tmp_path,
        ToolPacksConfig(enabled_packs=[pack_a, pack_b], disabled_packs=[], pinned_tools={}),
    )
    project = load_project(app_path)
    report = analyze_tool_health(project)
    assert report.pack_collisions == ["collision tool"]
    providers = report.pack_tools.get("collision tool", [])
    provider_ids = [provider.pack_id for provider in providers]
    assert provider_ids == sorted(provider_ids)
    assert provider_ids == sorted([pack_a, pack_b])
    assert any(issue.code == "packs.collision" for issue in report.issues)


def _install_pack(tmp_path: Path, fixture_name: str) -> str:
    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "packs" / fixture_name
    manifest = parse_pack_manifest(fixture_root / "pack.yaml")
    pack_dest = tmp_path / ".namel3ss" / "packs" / manifest.pack_id
    shutil.copytree(fixture_root, pack_dest)
    manifest_text = (pack_dest / "pack.yaml").read_text(encoding="utf-8")
    tools_text = (pack_dest / "tools.yaml").read_text(encoding="utf-8")
    digest = compute_pack_digest(manifest_text, tools_text)
    verification = {
        "pack_id": manifest.pack_id,
        "version": manifest.version,
        "digest": digest,
        "verified": True,
        "key_id": "test.key",
        "verified_at": "2024-01-01T00:00:00+00:00",
    }
    (pack_dest / "verification.json").write_text(
        json.dumps(verification, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest.pack_id
