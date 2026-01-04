from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.tools.bindings_yaml import ToolBinding

_DEFAULT_BINDINGS: dict[str, ToolBinding] = {
    "fetch_rate": ToolBinding(kind="python", entry="tools.fx_api:run"),
    "fetch_weather": ToolBinding(kind="python", entry="tools.weather_api:run"),
    "greeter": ToolBinding(kind="python", entry="tests.fixtures.tools.sample_tool:greet"),
}


def default_tool_bindings() -> dict[str, ToolBinding]:
    return dict(_DEFAULT_BINDINGS)


def default_tool_paths() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[4]
    if (repo_root / "tools").exists() or (repo_root / "tests").exists():
        return [repo_root]
    return []


__all__ = ["default_tool_bindings", "default_tool_paths"]
