from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.tools.bindings import load_tool_bindings


def test_bindings_yaml_rejects_inline_entries(tmp_path: Path) -> None:
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text('tools:\n  "greeter": "tools.greeter:run"\n', encoding="utf-8")
    with pytest.raises(Namel3ssError):
        load_tool_bindings(tmp_path)


def test_bindings_yaml_parses_runner_fields(tmp_path: Path) -> None:
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n'
        '  "greeter":\n'
        '    kind: "python"\n'
        '    entry: "tools.greeter:run"\n'
        '    runner: "service"\n'
        '    url: "http://127.0.0.1:8787/tools"\n'
        '    command: ["python", "-m", "namel3ss_tools.runner"]\n'
        '    env: {"LOG_LEVEL": "info"}\n',
        encoding="utf-8",
    )
    bindings = load_tool_bindings(tmp_path)
    binding = bindings["greeter"]
    assert binding.runner == "service"
    assert binding.url == "http://127.0.0.1:8787/tools"
    assert binding.command == ["python", "-m", "namel3ss_tools.runner"]
    assert binding.env == {"LOG_LEVEL": "info"}


def test_bindings_yaml_rejects_invalid_command(tmp_path: Path) -> None:
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n'
        '  "greeter":\n'
        '    kind: "python"\n'
        '    entry: "tools.greeter:run"\n'
        '    command: not-json\n',
        encoding="utf-8",
    )
    with pytest.raises(Namel3ssError):
        load_tool_bindings(tmp_path)


def test_bindings_yaml_allows_unknown_runner_string(tmp_path: Path) -> None:
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n'
        '  "greeter":\n'
        '    kind: "python"\n'
        '    entry: "tools.greeter:run"\n'
        '    runner: "bogus"\n',
        encoding="utf-8",
    )
    bindings = load_tool_bindings(tmp_path)
    assert bindings["greeter"].runner == "bogus"
