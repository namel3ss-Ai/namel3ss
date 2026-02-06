from __future__ import annotations

import json
import os
from pathlib import Path

from namel3ss.cli.main import main


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


def test_deps_add_python_updates_manifest(tmp_path: Path, capsys) -> None:
    app = tmp_path / "app.ai"
    app.write_text(APP_WITH_CAPABILITY, encoding="utf-8")

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["deps", "add", "requests@2.31.0", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "ok"
        assert payload["dependency_type"] == "python"
    finally:
        os.chdir(prev)

    manifest = (tmp_path / "namel3ss.toml").read_text(encoding="utf-8")
    assert "[runtime.dependencies]" in manifest
    assert "requests==2.31.0" in manifest


def test_deps_remove_python_updates_manifest(tmp_path: Path, capsys) -> None:
    app = tmp_path / "app.ai"
    app.write_text(APP_WITH_CAPABILITY, encoding="utf-8")
    (tmp_path / "namel3ss.toml").write_text(
        "[runtime.dependencies]\npython = [\"requests==2.31.0\"]\n",
        encoding="utf-8",
    )

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["deps", "remove", "requests==2.31.0", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "ok"
    finally:
        os.chdir(prev)

    manifest = (tmp_path / "namel3ss.toml").read_text(encoding="utf-8")
    assert "requests==2.31.0" not in manifest


def test_install_command_writes_unified_lockfile(tmp_path: Path, capsys) -> None:
    app = tmp_path / "app.ai"
    app.write_text(APP_WITH_CAPABILITY, encoding="utf-8")

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["install", "--skip-packages", "--skip-python", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "ok"
    finally:
        os.chdir(prev)

    assert (tmp_path / "namel3ss.lock").exists()
    assert (tmp_path / "namel3ss.lock.json").exists()


def test_deps_add_requires_dependency_management_capability(tmp_path: Path, capsys) -> None:
    app = tmp_path / "app.ai"
    app.write_text(APP_WITHOUT_CAPABILITY, encoding="utf-8")

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["deps", "add", "requests@2.31.0", "--json"]) == 1
        err = capsys.readouterr().err
        assert "dependency_management" in err
    finally:
        os.chdir(prev)


def test_deps_audit_json_returns_report(tmp_path: Path, capsys) -> None:
    app = tmp_path / "app.ai"
    app.write_text(APP_WITH_CAPABILITY, encoding="utf-8")
    (tmp_path / "namel3ss.toml").write_text("[dependencies]\n", encoding="utf-8")

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["install", "--skip-packages", "--skip-python"]) == 0
        capsys.readouterr()
        assert main(["deps", "audit", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert "summary" in payload
        assert "vulnerabilities" in payload
    finally:
        os.chdir(prev)
