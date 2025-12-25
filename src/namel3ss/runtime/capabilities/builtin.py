from __future__ import annotations

from namel3ss.runtime.packs.capabilities import ToolCapabilities


def _pure() -> ToolCapabilities:
    return ToolCapabilities(
        filesystem="none",
        network="none",
        env="none",
        subprocess="none",
        secrets=[],
    )


def _filesystem(level: str) -> ToolCapabilities:
    return ToolCapabilities(
        filesystem=level,
        network="none",
        env="none",
        subprocess="none",
        secrets=[],
    )


def _network() -> ToolCapabilities:
    return ToolCapabilities(
        filesystem="none",
        network="outbound",
        env="none",
        subprocess="none",
        secrets=[],
    )


_BUILTIN_CAPABILITIES: dict[str, ToolCapabilities] = {
    "convert text to lowercase": _pure(),
    "convert text to uppercase": _pure(),
    "slugify text": _pure(),
    "trim text": _pure(),
    "get current date and time": _pure(),
    "parse date and time": _pure(),
    "format date and time": _pure(),
    "read text file": _filesystem("read"),
    "write text file": _filesystem("write"),
    "read json file": _filesystem("read"),
    "write json file": _filesystem("write"),
    "get json from web": _network(),
    "post json to web": _network(),
}


def get_builtin_tool_capabilities(tool_name: str) -> ToolCapabilities | None:
    return _BUILTIN_CAPABILITIES.get(tool_name)


__all__ = ["get_builtin_tool_capabilities"]
