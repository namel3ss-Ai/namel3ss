from __future__ import annotations

import hashlib
import json
from pathlib import Path

from namel3ss.cli.build_command import run_build_cli_command
from namel3ss.cli.deploy_command import run_deploy_cli_command
from namel3ss.packaging.build import build_deployable_bundle
from namel3ss.packaging.deploy import deploy_bundle_archive


def _write_app(path: Path) -> None:
    path.write_text(
        'spec is "1.0"\n\n'
        'flow "send_message":\n'
        '  return "ok"\n\n'
        'page "home":\n'
        '  title is "Packaging Demo"\n'
        '  text is "Ready"\n',
        encoding="utf-8",
    )


def _seed_assets(project_root: Path) -> None:
    (project_root / "themes").mkdir(parents=True, exist_ok=True)
    (project_root / "themes" / "demo.json").write_text('{"base_theme":"default","overrides":{}}', encoding="utf-8")
    locales = project_root / "i18n" / "locales"
    locales.mkdir(parents=True, exist_ok=True)
    (locales / "en.json").write_text(
        json.dumps(
            {
                "locale": "en",
                "fallback_locale": "en",
                "messages": {"pages.0.title": {"en": "Packaging Demo"}},
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_build_deployable_bundle_is_repeatable(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    _write_app(app_path)
    _seed_assets(tmp_path)

    first = build_deployable_bundle(app_path, out_dir=tmp_path / "dist", target="service", include_profile=False)
    second = build_deployable_bundle(app_path, out_dir=tmp_path / "dist", target="service", include_profile=False)
    assert first.package_manifest.read_text(encoding="utf-8") == second.package_manifest.read_text(encoding="utf-8")
    assert hashlib.sha256(first.archive.read_bytes()).hexdigest() == hashlib.sha256(second.archive.read_bytes()).hexdigest()


def test_build_deployable_bundle_can_emit_profile(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    _write_app(app_path)
    bundle = build_deployable_bundle(
        app_path,
        out_dir=tmp_path / "dist",
        target="local",
        include_profile=True,
        profile_iterations=1,
    )
    assert bundle.profile is not None
    assert (bundle.root / "performance_profile.json").exists()


def test_deploy_bundle_archive_writes_deterministic_report(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    _write_app(app_path)
    bundle = build_deployable_bundle(app_path, out_dir=tmp_path / "dist", target="edge", include_profile=False)
    deployed = deploy_bundle_archive(bundle.archive, out_dir=tmp_path / "deploy", channels=("npm", "filesystem"))
    assert deployed.report_path.exists()
    assert [item.channel for item in deployed.records] == ["filesystem", "npm"]


def test_build_and_deploy_cli_commands(tmp_path: Path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    _write_app(app_path)
    previous = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        assert run_build_cli_command(["app.ai", "--out", "dist", "--target", "service", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        archive = payload["bundle"]["archive"]
        assert run_deploy_cli_command([archive, "--out", "deploy", "--channel", "filesystem", "--json"]) == 0
        deploy_payload = json.loads(capsys.readouterr().out)
        assert deploy_payload["channels"] == ["filesystem"]
    finally:
        os.chdir(previous)
