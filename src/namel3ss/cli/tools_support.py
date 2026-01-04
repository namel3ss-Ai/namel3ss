from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.config.loader import load_config
from namel3ss.runtime.packs.registry import load_pack_registry
from namel3ss.runtime.tools.bindings import bindings_path
from namel3ss.runtime.tools.bindings_yaml import ToolBinding, render_bindings_yaml
from namel3ss.templates.tools import ToolField, render_tool_module
from namel3ss.utils.slugify import slugify_tool_name


DEFAULT_CONVENTION = "slug-run"
SUPPORTED_CONVENTIONS = {DEFAULT_CONVENTION}


@dataclass(frozen=True)
class StubPlan:
    tool_name: str
    entry: str
    path: Path
    content: str
    exists: bool


@dataclass(frozen=True)
class FromAppConfig:
    app_path: str | None
    convention: str
    dry: bool
    allow_overwrite: bool


@dataclass(frozen=True)
class BindingsPlan:
    missing: list[str]
    proposed: dict[str, ToolBinding]
    stubs: list[StubPlan]
    conflicts: list[Path]
    preview: str


def parse_from_app_args(args: list[str]) -> FromAppConfig:
    app_path = None
    convention = DEFAULT_CONVENTION
    dry = False
    yes = False
    overwrite = False
    idx = 0
    while idx < len(args):
        item = args[idx]
        if item == "--from-app":
            if idx + 1 < len(args) and args[idx + 1].endswith(".ai"):
                app_path = args[idx + 1]
                idx += 2
            else:
                idx += 1
            continue
        if item.startswith("--convention="):
            convention = item.split("=", 1)[1]
            idx += 1
            continue
        if item == "--convention":
            if idx + 1 >= len(args):
                raise Namel3ssError(missing_convention_message())
            convention = args[idx + 1]
            idx += 2
            continue
        if item == "--dry":
            dry = True
            idx += 1
            continue
        if item == "--yes":
            yes = True
            idx += 1
            continue
        if item == "--overwrite":
            overwrite = True
            idx += 1
            continue
        if item.startswith("-"):
            raise Namel3ssError(unknown_flag_message(item))
        if item.endswith(".ai") and app_path is None:
            app_path = item
            idx += 1
            continue
        raise Namel3ssError(unknown_args_message([item]))
    allow_overwrite = yes and overwrite
    return FromAppConfig(app_path=app_path, convention=convention, dry=dry, allow_overwrite=allow_overwrite)


def plan_stub(app_root: Path, tool_decl, tool_name: str, slug: str) -> StubPlan:
    module_path = app_root / "tools" / f"{slug}.py"
    exists = module_path.exists()
    input_fields = [ToolField(name=field.name, field_type=field.type_name, required=field.required) for field in tool_decl.input_fields]
    output_fields = [ToolField(name=field.name, field_type=field.type_name, required=field.required) for field in tool_decl.output_fields]
    content = render_tool_module(
        tool_name=tool_name,
        function_name="run",
        input_fields=input_fields,
        output_fields=output_fields,
    )
    return StubPlan(tool_name=tool_name, entry=f"tools.{slug}:run", path=module_path, content=content, exists=exists)


def build_bindings_plan(app_root: Path, program, bindings: dict[str, ToolBinding]) -> BindingsPlan:
    pack_tools = _active_pack_tools(app_root)
    python_tools = {
        name: tool
        for name, tool in program.tools.items()
        if tool.kind == "python" and name not in pack_tools
    }
    missing = sorted(name for name in python_tools if name not in bindings)
    proposed = dict(bindings)
    stubs: list[StubPlan] = []
    for name in missing:
        slug = slugify_tool_name(name)
        entry = f"tools.{slug}:run"
        proposed[name] = ToolBinding(kind="python", entry=entry)
        stubs.append(plan_stub(app_root, python_tools[name], name, slug))
    conflicts = [stub.path for stub in stubs if stub.exists]
    preview = render_bindings_yaml(proposed)
    return BindingsPlan(
        missing=missing,
        proposed=proposed,
        stubs=stubs,
        conflicts=conflicts,
        preview=preview,
    )


def _active_pack_tools(app_root: Path) -> set[str]:
    config = load_config(root=app_root)
    registry = load_pack_registry(app_root, config)
    active: set[str] = set()
    for name, providers in registry.tools.items():
        for provider in providers:
            if provider.source == "builtin_pack" or (provider.verified and provider.enabled):
                active.add(name)
                break
    return active


def bindings_payload(bindings: dict[str, ToolBinding]) -> dict[str, dict]:
    payload = {}
    for name, binding in sorted(bindings.items()):
        payload[name] = {
            "kind": binding.kind,
            "entry": binding.entry,
            "runner": binding.runner,
            "url": binding.url,
            "image": binding.image,
            "command": binding.command,
            "env": binding.env,
            "purity": binding.purity,
            "timeout_ms": binding.timeout_ms,
            "sandbox": binding.sandbox,
            "enforcement": binding.enforcement,
        }
    return payload


def build_dry_payload(app_root: Path, missing: list[str], stubs: list[StubPlan], preview: str, conflicts: list[Path]) -> dict:
    return {
        "status": "dry_run",
        "bindings_path": str(bindings_path(app_root)),
        "missing_bindings": missing,
        "bindings_preview": preview,
        "stubs": [
            {
                "path": str(stub.path),
                "entry": stub.entry,
                "exists": stub.exists,
                "content": stub.content,
            }
            for stub in stubs
        ],
        "conflicts": [str(path) for path in conflicts],
    }


def print_dry_run(payload: dict) -> None:
    print("Bindings preview:")
    print(payload["bindings_preview"].rstrip())
    if payload["stubs"]:
        print("Tool stubs:")
        for stub in payload["stubs"]:
            status = "exists" if stub["exists"] else "create"
            print(f"- {stub['path']} status {status}")
    if payload["conflicts"]:
        print("Conflicts:")
        for path in payload["conflicts"]:
            print(f"- {path}")


def stub_conflict_message(conflicts: list[Path]) -> str:
    conflict_list = "\n".join(f"- {path}" for path in conflicts)
    return build_guidance_message(
        what="Tool stub files already exist.",
        why=f"Conflicts found:\n{conflict_list}",
        fix="Re-run with --yes --overwrite to replace existing stubs.",
        example="n3 tools bind --from-app --yes --overwrite",
    )


def unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="The tools command received unexpected arguments.",
        fix="Remove the extra arguments and try again.",
        example="n3 tools status",
    )


def unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="The tools command does not recognize this flag.",
        fix="Remove the flag and try again.",
        example='n3 tools bind "get data" --entry "tools.http:get_json"',
    )


def missing_tool_message() -> str:
    return build_guidance_message(
        what="Tool name is missing.",
        why="You must specify which tool to bind or unbind.",
        fix="Provide the tool name before --entry.",
        example='n3 tools bind "get data" --entry "tools.http:get_json"',
    )


def missing_entry_message() -> str:
    return build_guidance_message(
        what="Entry is missing.",
        why="Bindings require a module:function entry.",
        fix="Provide --entry with a Python module and function.",
        example='n3 tools bind "get data" --entry "tools.http:get_json"',
    )


def missing_convention_message() -> str:
    return build_guidance_message(
        what="Convention is missing.",
        why="--convention requires a value.",
        fix=f"Use one of: {', '.join(sorted(SUPPORTED_CONVENTIONS))}.",
        example="n3 tools bind --from-app --convention slug-run",
    )


def unknown_convention_message(convention: str) -> str:
    return build_guidance_message(
        what=f"Unknown convention '{convention}'.",
        why=f"Supported conventions are: {', '.join(sorted(SUPPORTED_CONVENTIONS))}.",
        fix="Use the default convention or omit the flag.",
        example="n3 tools bind --from-app",
    )


def extract_app_path(args: list[str]) -> tuple[str | None, list[str]]:
    if args and args[0].endswith(".ai"):
        return args[0], args[1:]
    return None, args


__all__ = [
    "DEFAULT_CONVENTION",
    "SUPPORTED_CONVENTIONS",
    "BindingsPlan",
    "FromAppConfig",
    "StubPlan",
    "build_bindings_plan",
    "bindings_payload",
    "build_dry_payload",
    "extract_app_path",
    "missing_convention_message",
    "missing_entry_message",
    "missing_tool_message",
    "parse_from_app_args",
    "plan_stub",
    "print_dry_run",
    "stub_conflict_message",
    "unknown_args_message",
    "unknown_convention_message",
    "unknown_flag_message",
]
