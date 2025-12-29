from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from namel3ss.cli.main import main


def _write_app(root: Path) -> None:
    (root / "app.ai").write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")


def test_deps_status_detects_none(tmp_path, capsys):
    _write_app(tmp_path)
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["deps", "status", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["dependency_file_detected"] is None
        assert payload["deps_source"] == "none"
        assert payload["exists"] is False
    finally:
        os.chdir(prev)


def test_deps_status_prefers_pyproject(tmp_path, capsys):
    _write_app(tmp_path)
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = \"demo\"\ndependencies = [\"httpx==0.25.0\"]\n",
        encoding="utf-8",
    )
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["deps", "status", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["dependency_file_detected"].endswith("pyproject.toml")
        assert payload["deps_source"] == "pyproject"
        assert "warning" in payload
    finally:
        os.chdir(prev)


def test_deps_install_creates_venv_and_lockfile(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")

    calls = []

    def fake_run(cmd, cwd, capture_output, text, env, check=False):
        calls.append(cmd)
        if cmd[1:3] == ["-m", "venv"]:
            venv_path = Path(cmd[3])
            venv_path.mkdir(parents=True, exist_ok=True)
            py_path = venv_path / "bin" / "python"
            py_path.parent.mkdir(parents=True, exist_ok=True)
            py_path.write_text("", encoding="utf-8")
            (venv_path / "pyvenv.cfg").write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if "freeze" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "requests==2.31.0\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("namel3ss.cli.deps_mode.subprocess.run", fake_run)

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["deps", "install", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "ok"
        lockfile = tmp_path / "requirements.lock.txt"
        assert lockfile.exists()
        assert "requests==2.31.0" in lockfile.read_text(encoding="utf-8")
    finally:
        os.chdir(prev)

    assert any(cmd[:3] == [payload["python_path"], "-m", "pip"] for cmd in calls)


def test_deps_lock_writes_lockfile(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")

    def fake_run(cmd, cwd, capture_output, text, env, check=False):
        if cmd[1:3] == ["-m", "venv"]:
            venv_path = Path(cmd[3])
            venv_path.mkdir(parents=True, exist_ok=True)
            py_path = venv_path / "bin" / "python"
            py_path.parent.mkdir(parents=True, exist_ok=True)
            py_path.write_text("", encoding="utf-8")
            (venv_path / "pyvenv.cfg").write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if "freeze" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "demo==0.0.1\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("namel3ss.cli.deps_mode.subprocess.run", fake_run)

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["deps", "lock", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["lockfile"].endswith("requirements.lock.txt")
    finally:
        os.chdir(prev)


def test_deps_install_failure_is_friendly(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")

    def fake_run(cmd, cwd, capture_output, text, env, check=False):
        if cmd[1:3] == ["-m", "venv"]:
            venv_path = Path(cmd[3])
            venv_path.mkdir(parents=True, exist_ok=True)
            py_path = venv_path / "bin" / "python"
            py_path.parent.mkdir(parents=True, exist_ok=True)
            py_path.write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 1, "", "pip failed")

    monkeypatch.setattr("namel3ss.cli.deps_mode.subprocess.run", fake_run)

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["deps", "install"]) == 1
        err = capsys.readouterr().err
        assert "dependency install failed" in err.lower()
    finally:
        os.chdir(prev)


def test_deps_invalid_python_path(tmp_path, capsys):
    _write_app(tmp_path)
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["deps", "install", "--python", str(tmp_path / "missing"), "--json"]) == 1
        err = capsys.readouterr().err
        assert "python interpreter not found" in err.lower()
    finally:
        os.chdir(prev)
