from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.studio.dependencies_api import apply_dependencies_payload, get_dependencies_payload


APP_WITH_CAPABILITY = '''spec is "1.0"

capabilities:
  dependency_management

flow "demo":
  return "ok"
'''

APP_WITHOUT_CAPABILITY = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def test_get_dependencies_payload_returns_status(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_WITH_CAPABILITY, encoding="utf-8")
    payload = get_dependencies_payload("", str(app_path))
    assert payload["ok"] is True
    assert payload["status"]["status"] == "ok"


def test_apply_dependencies_payload_add_python_updates_manifest(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_WITH_CAPABILITY, encoding="utf-8")

    payload = apply_dependencies_payload(
        "",
        {"action": "add_python", "spec": "requests@2.31.0"},
        str(app_path),
    )
    assert payload["status"] == "ok"

    manifest = (tmp_path / "namel3ss.toml").read_text(encoding="utf-8")
    assert "[runtime.dependencies]" in manifest
    assert "requests==2.31.0" in manifest


def test_apply_dependencies_payload_requires_capability_for_install(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_WITHOUT_CAPABILITY, encoding="utf-8")

    with pytest.raises(Namel3ssError):
        apply_dependencies_payload("", {"action": "install"}, str(app_path))


def test_apply_dependencies_payload_remove_python_updates_manifest(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_WITH_CAPABILITY, encoding="utf-8")
    apply_dependencies_payload(
        "",
        {"action": "add_python", "spec": "requests@2.31.0"},
        str(app_path),
    )

    payload = apply_dependencies_payload(
        "",
        {"action": "remove_python", "spec": "requests==2.31.0"},
        str(app_path),
    )
    assert payload["status"] == "ok"
    manifest = (tmp_path / "namel3ss.toml").read_text(encoding="utf-8")
    assert "requests==2.31.0" not in manifest
