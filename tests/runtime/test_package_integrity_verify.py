from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from namel3ss.cli.targets_store import BUILD_META_FILENAME, build_dir, latest_pointer_path, write_json
from namel3ss.governance.verify import run_verify
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def test_package_integrity_ok_without_packages_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("N3_PACKAGE_INTEGRITY_REQUIRED", raising=False)
    app_path = _write_app(tmp_path)
    digest = _write_lockfile(tmp_path, packages=[])
    _write_build_metadata(tmp_path, digest)

    payload = run_verify(app_path, target="local", prod=False, config_root=tmp_path)
    check = _find_check(payload, "package_integrity")

    assert payload["status"] == "ok"
    assert check["status"] == "ok"
    assert check["message"] == "Packages match the lockfile and include license metadata."
    assert check.get("details", {}).get("skipped") is True
    assert check.get("details", {}).get("reason") == "packages directory missing and packages not required"


def test_package_integrity_fails_when_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("N3_PACKAGE_INTEGRITY_REQUIRED", "1")
    app_path = _write_app(tmp_path)
    digest = _write_lockfile(tmp_path, packages=[])
    _write_build_metadata(tmp_path, digest)

    payload = run_verify(app_path, target="local", prod=False, config_root=tmp_path)
    check = _find_check(payload, "package_integrity")

    assert payload["status"] == "fail"
    assert check["status"] == "fail"
    issues = check.get("details", {}).get("issues", [])
    assert "(packages): packages/ directory is missing." in issues


def _write_app(root: Path) -> Path:
    app_path = root / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    return app_path


def _write_lockfile(root: Path, *, packages: list[dict]) -> str:
    payload = {
        "lockfile_version": 1,
        "roots": [],
        "packages": packages,
    }
    path = root / LOCKFILE_FILENAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    return digest


def _write_build_metadata(root: Path, lockfile_digest: str) -> None:
    build_id = "spec"
    latest_path = latest_pointer_path(root, "local")
    build_path = build_dir(root, "local", build_id) / BUILD_META_FILENAME
    write_json(latest_path, {"build_id": build_id})
    write_json(build_path, {"build_id": build_id, "lockfile_digest": lockfile_digest})


def _find_check(payload: dict, check_id: str) -> dict:
    for check in payload.get("checks", []):
        if check.get("id") == check_id:
            return check
    raise AssertionError(f"Missing check {check_id}")
