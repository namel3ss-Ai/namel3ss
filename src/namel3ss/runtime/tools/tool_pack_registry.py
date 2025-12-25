from __future__ import annotations

from dataclasses import dataclass


TOOL_PACK_VERSION = "v1"


@dataclass(frozen=True)
class ToolPackBinding:
    tool_name: str
    entry: str
    pack_name: str
    version: str | None = None


_PACKS: dict[str, ToolPackBinding] = {}


def _register(tool_name: str, entry: str, pack_name: str) -> None:
    _PACKS[tool_name] = ToolPackBinding(
        tool_name=tool_name,
        entry=entry,
        pack_name=pack_name,
        version=TOOL_PACK_VERSION,
    )


_register("convert text to lowercase", "namel3ss.tool_packs.text:lower", "text")
_register("convert text to uppercase", "namel3ss.tool_packs.text:upper", "text")
_register("slugify text", "namel3ss.tool_packs.text:slugify", "text")
_register("trim text", "namel3ss.tool_packs.text:trim", "text")

_register("get current date and time", "namel3ss.tool_packs.datetime:now", "datetime")
_register("parse date and time", "namel3ss.tool_packs.datetime:parse", "datetime")
_register("format date and time", "namel3ss.tool_packs.datetime:format", "datetime")

_register("read text file", "namel3ss.tool_packs.file:read_text", "file")
_register("write text file", "namel3ss.tool_packs.file:write_text", "file")
_register("read json file", "namel3ss.tool_packs.file:read_json", "file")
_register("write json file", "namel3ss.tool_packs.file:write_json", "file")

_register("get json from web", "namel3ss.tool_packs.http:get_json", "http")
_register("post json to web", "namel3ss.tool_packs.http:post_json", "http")


def get_tool_pack_binding(tool_name: str) -> ToolPackBinding | None:
    return _PACKS.get(tool_name)


def is_tool_pack_tool(tool_name: str) -> bool:
    return tool_name in _PACKS


def list_tool_pack_tools() -> list[str]:
    return sorted(_PACKS.keys())


__all__ = [
    "TOOL_PACK_VERSION",
    "ToolPackBinding",
    "get_tool_pack_binding",
    "is_tool_pack_tool",
    "list_tool_pack_tools",
]
