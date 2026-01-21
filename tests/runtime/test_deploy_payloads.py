from __future__ import annotations

import json
from pathlib import Path

from namel3ss.beta_lock.repo_clean import repo_dirty_entries
from namel3ss.cli.build_mode import run_build_command
from namel3ss.cli.builds import read_latest_build_id
from namel3ss.cli.promotion_state import record_promotion
from namel3ss.cli.targets_store import BUILD_BASE_DIR
from namel3ss.config.model import AppConfig
from namel3ss.module_loader import load_project
from namel3ss.runtime.deploy_routes import get_build_payload, get_deploy_payload
from namel3ss.runtime.environment_summary import build_environment_summary


APP_SOURCE = '''spec is "1.0"

flow "demo":
  log info secret("stripe_key")
  return "ok"
'''


def _write_app(tmp_path: Path) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    return app_path


def test_build_payload_is_stable(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    assert run_build_command([app_path.as_posix(), "--target", "service"]) == 0
    build_id = read_latest_build_id(tmp_path, "service")
    assert build_id
    build_root = tmp_path / BUILD_BASE_DIR / "service" / build_id
    meta_one = json.loads((build_root / "build.json").read_text(encoding="utf-8"))
    report_one = json.loads((build_root / "build_report.json").read_text(encoding="utf-8"))
    entry_one = json.loads((build_root / "entry.json").read_text(encoding="utf-8"))

    assert run_build_command([app_path.as_posix(), "--target", "service"]) == 0
    build_id_again = read_latest_build_id(tmp_path, "service")
    assert build_id_again == build_id
    meta_two = json.loads((build_root / "build.json").read_text(encoding="utf-8"))
    report_two = json.loads((build_root / "build_report.json").read_text(encoding="utf-8"))
    entry_two = json.loads((build_root / "entry.json").read_text(encoding="utf-8"))
    assert meta_one == meta_two
    assert report_one == report_two
    assert entry_one == entry_two

    payload_one = get_build_payload(tmp_path, app_path)
    payload_two = get_build_payload(tmp_path, app_path)
    assert payload_one == payload_two
    assert payload_one.get("build_root") == ".namel3ss/build"
    builds = payload_one.get("builds", [])
    targets = [entry.get("target") for entry in builds]
    assert targets == sorted(targets)
    service_builds = [entry for entry in builds if entry.get("target") == "service"]
    assert service_builds
    service_entry = service_builds[0]
    assert service_entry.get("status") == "ready"
    assert service_entry.get("entry_instructions")
    assert service_entry.get("location")


def test_deploy_payload_is_stable(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    project = load_project(app_path)
    assert run_build_command([app_path.as_posix(), "--target", "service"]) == 0
    build_id = read_latest_build_id(tmp_path, "service")
    assert build_id
    record_promotion(tmp_path, "service", build_id)
    payload_one = get_deploy_payload(tmp_path, app_path, program=project.program)
    payload_two = get_deploy_payload(tmp_path, app_path, program=project.program)
    assert payload_one == payload_two
    assert payload_one.get("status") == "active"
    assert payload_one.get("active", {}).get("build_id") == build_id
    env_summary = payload_one.get("environment", {})
    assert env_summary.get("ok") is True


def test_environment_summary_is_redacted(tmp_path: Path, monkeypatch) -> None:
    app_path = _write_app(tmp_path)
    env_path = tmp_path / ".env"
    secret_value = "sk-test-secret"
    env_path.write_text(
        f"N3_SECRET_STRIPE_KEY={secret_value}\nN3_DATABASE_URL=postgres://...\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("N3_SECRET_STRIPE_KEY", raising=False)
    monkeypatch.delenv("N3_DATABASE_URL", raising=False)
    config = AppConfig()
    config.persistence.target = "postgres"
    program = load_project(app_path).program
    summary = build_environment_summary(
        tmp_path,
        app_path,
        program=program,
        config=config,
        sources=[],
    )
    summary_again = build_environment_summary(
        tmp_path,
        app_path,
        program=program,
        config=config,
        sources=[],
    )
    assert summary == summary_again
    blob = json.dumps(summary, sort_keys=True)
    assert secret_value not in blob
    assert tmp_path.as_posix() not in blob
    required_names = [entry.get("name") for entry in summary.get("required", [])]
    assert "N3_DATABASE_URL" in required_names
    assert "N3_SECRET_STRIPE_KEY" in required_names


def test_deploy_payload_does_not_dirty_repo(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    baseline = set(repo_dirty_entries(root))
    app_path = _write_app(tmp_path)
    project = load_project(app_path)
    _ = get_build_payload(tmp_path, app_path)
    _ = get_deploy_payload(tmp_path, app_path, program=project.program)
    dirty = set(repo_dirty_entries(root))
    assert dirty == baseline
