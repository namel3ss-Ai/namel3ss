from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.runtime.tools.runners.base import ToolRunnerRequest
from namel3ss.runtime.tools.runners.container_runner import ContainerRunner


def test_container_runner_executes(monkeypatch, tmp_path: Path) -> None:
    binding = ToolBinding(
        kind="python",
        entry="tools.greeter:run",
        runner="container",
        image="ghcr.io/namel3ss/tools:latest",
        command=["python", "-m", "namel3ss_tools.runner"],
        env={"A": "1", "B": "2"},
    )
    request = ToolRunnerRequest(
        tool_name="greeter",
        kind="python",
        entry=binding.entry,
        payload={"name": "Ada"},
        timeout_ms=1000,
        trace_id="trace-1",
        app_root=tmp_path,
        flow_name="demo",
        binding=binding,
        config=AppConfig(),
    )
    seen: dict[str, object] = {}

    monkeypatch.setattr(
        "namel3ss.runtime.tools.runners.container_runner.detect_container_runtime",
        lambda: "docker",
    )

    def fake_run(cmd, input, text, capture_output, timeout, check):  # type: ignore[override]
        seen["cmd"] = cmd
        seen["input"] = input
        output = json.dumps({"ok": True, "result": {"ok": True}})
        return subprocess.CompletedProcess(cmd, 0, stdout=output, stderr="")

    monkeypatch.setattr("namel3ss.runtime.tools.runners.container_runner.subprocess.run", fake_run)

    result = ContainerRunner().execute(request)
    assert result.ok is True
    assert result.output == {"ok": True}
    assert result.metadata["runner"] == "container"
    assert result.metadata["container_runtime"] == "docker"
    assert result.metadata["image"] == "ghcr.io/namel3ss/tools:latest"
    assert result.metadata["command"] == "python -m namel3ss_tools.runner"

    cmd = seen["cmd"]
    assert cmd == [
        "docker",
        "run",
        "--rm",
        "-i",
        "-e",
        "A=1",
        "-e",
        "B=2",
        "ghcr.io/namel3ss/tools:latest",
        "python",
        "-m",
        "namel3ss_tools.runner",
    ]
    payload = json.loads(seen["input"])
    assert payload["tool"] == "greeter"
    assert payload["entry"] == "tools.greeter:run"


def test_container_runner_missing_runtime(monkeypatch, tmp_path: Path) -> None:
    binding = ToolBinding(kind="python", entry="tools.greeter:run", runner="container", image="img")
    request = ToolRunnerRequest(
        tool_name="greeter",
        kind="python",
        entry=binding.entry,
        payload={},
        timeout_ms=1000,
        trace_id="trace-1",
        app_root=tmp_path,
        flow_name=None,
        binding=binding,
        config=AppConfig(),
    )
    monkeypatch.setattr(
        "namel3ss.runtime.tools.runners.container_runner.detect_container_runtime",
        lambda: None,
    )
    with pytest.raises(Namel3ssError) as exc:
        ContainerRunner().execute(request)
    assert "container runtime" in str(exc.value).lower()


def test_container_runner_missing_image(monkeypatch, tmp_path: Path) -> None:
    binding = ToolBinding(kind="python", entry="tools.greeter:run", runner="container")
    request = ToolRunnerRequest(
        tool_name="greeter",
        kind="python",
        entry=binding.entry,
        payload={},
        timeout_ms=1000,
        trace_id="trace-1",
        app_root=tmp_path,
        flow_name=None,
        binding=binding,
        config=AppConfig(),
    )
    monkeypatch.setattr(
        "namel3ss.runtime.tools.runners.container_runner.detect_container_runtime",
        lambda: "docker",
    )
    with pytest.raises(Namel3ssError) as exc:
        ContainerRunner().execute(request)
    assert "image" in str(exc.value).lower()
