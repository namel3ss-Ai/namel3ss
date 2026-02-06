from __future__ import annotations

import sys
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.server.concurrency import load_concurrency_config


def test_concurrency_config_defaults(tmp_path: Path) -> None:
    config = load_concurrency_config(project_root=tmp_path)
    assert config.server_mode == "threaded"
    assert config.max_threads == 8
    assert config.worker_processes == 1
    payload = config.to_dict()
    assert payload["server_mode"] == "threaded"
    assert payload["max_threads"] == 8
    assert payload["worker_processes"] == 1


def test_concurrency_config_file_and_env_override(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "concurrency.yaml").write_text(
        "server_mode: single\nmax_threads: 2\nworker_processes: 3\ncompiled_cache_enabled: false\n",
        encoding="utf-8",
    )
    config = load_concurrency_config(project_root=tmp_path)
    assert config.server_mode == "single"
    assert config.max_threads == 2
    assert config.worker_processes == 3
    assert config.compiled_cache_enabled is False

    monkeypatch.setenv("N3_SERVER_MODE", "threaded")
    monkeypatch.setenv("N3_MAX_THREADS", "5")
    config_env = load_concurrency_config(project_root=tmp_path)
    assert config_env.server_mode == "threaded"
    assert config_env.max_threads == 5


def test_concurrency_config_rejects_invalid_values(tmp_path: Path) -> None:
    (tmp_path / "concurrency.yaml").write_text(
        "server_mode: threaded\nmax_threads: 0\n",
        encoding="utf-8",
    )
    with pytest.raises(Namel3ssError) as exc:
        load_concurrency_config(project_root=tmp_path)
    assert "max_threads" in exc.value.message


def test_concurrency_config_requires_free_threaded_when_requested(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "concurrency.yaml").write_text(
        "require_free_threaded: true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "_is_gil_enabled", lambda: True, raising=False)
    with pytest.raises(Namel3ssError) as exc:
        load_concurrency_config(project_root=tmp_path)
    assert "Free-threaded Python is required" in exc.value.message
