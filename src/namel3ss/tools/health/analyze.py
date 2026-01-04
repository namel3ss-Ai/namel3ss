from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader.types import ProjectLoadResult
from namel3ss.config.loader import load_config
from namel3ss.runtime.packs.registry import load_pack_registry
from namel3ss.runtime.tools.bindings import load_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.runtime.tools.entry_validation import validate_node_tool_entry, validate_python_tool_entry
from namel3ss.runtime.tools.runners.container_detect import detect_container_runtime
from namel3ss.utils.slugify import slugify_tool_name

from namel3ss.tools.health.model import ToolDeclInfo, ToolHealthReport, ToolIssue
from namel3ss.tools.health.pack_analysis import active_pack_tool_names, collect_pack_inventory


def analyze_tool_health(project: ProjectLoadResult) -> ToolHealthReport:
    app_root = project.app_path.parent
    config = load_config(app_path=project.app_path, root=app_root)
    declared_tools = _collect_declared_tools(project)
    declared_map = {tool.name: tool for tool in declared_tools}
    duplicate_decls, duplicate_issues = _find_duplicate_decls(project)

    bindings, bindings_valid, bindings_error, bindings_issues = _load_bindings(app_root)
    pack_registry = load_pack_registry(app_root, config)
    pack_tools, pack_summaries, pack_issues, pack_collisions = collect_pack_inventory(pack_registry, config)

    issues: list[ToolIssue] = []
    issues.extend(duplicate_issues)
    issues.extend(bindings_issues)
    issues.extend(pack_issues)

    collisions: list[str] = []
    missing_bindings: list[str] = []
    unused_bindings: list[str] = []
    invalid_bindings: list[str] = []
    invalid_runners: list[str] = []
    service_missing_urls: list[str] = []
    container_missing_images: list[str] = []
    container_missing_runtime: list[str] = []
    empty_io: list[str] = []

    if bindings_valid:
        active_pack_tools = active_pack_tool_names(pack_tools)
        collisions = sorted(name for name in bindings if name in active_pack_tools)
        for name in collisions:
            issues.append(
                ToolIssue(
                    code="tools.collision",
                    message=_collision_message(name),
                    severity="error",
                    tool_name=name,
                    line=_line_for_tool(declared_map, name),
                    column=_column_for_tool(declared_map, name),
                )
            )
        invalid_bindings, invalid_issues = _find_invalid_bindings(bindings)
        issues.extend(invalid_issues)
        (
            invalid_runners,
            service_missing_urls,
            container_missing_images,
            container_missing_runtime,
            runner_issues,
        ) = _find_runner_issues(bindings, config)
        issues.extend(runner_issues)

        declared_names = {tool.name for tool in declared_tools}
        pack_names = set(active_pack_tool_names(pack_tools))
        missing_bindings = sorted(
            name
            for name, tool in declared_map.items()
            if tool.kind in {"python", "node"} and name not in bindings and name not in pack_names
        )
        for name in missing_bindings:
            issues.append(
                ToolIssue(
                    code="tools.missing_binding",
                    message=_missing_binding_message(name),
                    severity="warning",
                    tool_name=name,
                    line=_line_for_tool(declared_map, name),
                    column=_column_for_tool(declared_map, name),
                )
            )
        unused_bindings = sorted(name for name in bindings if name not in declared_names and name not in pack_names)
        for name in unused_bindings:
            issues.append(
                ToolIssue(
                    code="tools.unused_binding",
                    message=_unused_binding_message(name),
                    severity="warning",
                    tool_name=name,
                )
            )

    empty_io, empty_io_issues = _find_empty_io(declared_tools)
    issues.extend(empty_io_issues)

    return ToolHealthReport(
        declared_tools=declared_tools,
        bindings=bindings,
        pack_tools=pack_tools,
        pack_collisions=pack_collisions,
        packs=pack_summaries,
        missing_bindings=missing_bindings,
        unused_bindings=unused_bindings,
        collisions=collisions,
        invalid_bindings=invalid_bindings,
        invalid_runners=invalid_runners,
        service_missing_urls=service_missing_urls,
        container_missing_images=container_missing_images,
        container_missing_runtime=container_missing_runtime,
        empty_io=empty_io,
        duplicate_decls=duplicate_decls,
        issues=issues,
        bindings_valid=bindings_valid,
        bindings_error=bindings_error,
    )


def _collect_declared_tools(project: ProjectLoadResult) -> list[ToolDeclInfo]:
    tools: list[ToolDeclInfo] = []
    for tool in project.program.tools.values():
        tools.append(
            ToolDeclInfo(
                name=tool.name,
                kind=tool.kind,
                input_fields=len(tool.input_fields),
                output_fields=len(tool.output_fields),
                line=getattr(tool, "line", None),
                column=getattr(tool, "column", None),
            )
        )
    return tools


def _find_duplicate_decls(project: ProjectLoadResult) -> tuple[list[str], list[ToolIssue]]:
    seen: set[str] = set()
    duplicates: list[str] = []
    issues: list[ToolIssue] = []
    for tool in project.app_ast.tools:
        if tool.name in seen:
            duplicates.append(tool.name)
            issues.append(
                ToolIssue(
                    code="tools.duplicate_decl",
                    message=_duplicate_decl_message(tool.name),
                    severity="error",
                    tool_name=tool.name,
                    line=tool.line,
                    column=tool.column,
                )
            )
        else:
            seen.add(tool.name)
    return sorted(set(duplicates)), issues


def _load_bindings(app_root: Path) -> tuple[dict[str, ToolBinding], bool, str | None, list[ToolIssue]]:
    issues: list[ToolIssue] = []
    try:
        bindings = load_tool_bindings(app_root)
        return bindings, True, None, issues
    except Namel3ssError as err:
        issues.append(
            ToolIssue(
                code="tools.bindings_invalid",
                message=str(err),
                severity="error",
            )
        )
        return {}, False, str(err), issues




def _find_invalid_bindings(bindings: dict[str, ToolBinding]) -> tuple[list[str], list[ToolIssue]]:
    invalid: list[str] = []
    issues: list[ToolIssue] = []
    for name, binding in bindings.items():
        entry = getattr(binding, "entry", None)
        if not isinstance(entry, str):
            invalid.append(name)
            issues.append(
                ToolIssue(
                    code="tools.invalid_binding",
                    message=_invalid_binding_message(name),
                    severity="error",
                    tool_name=name,
                )
            )
            continue
        try:
            if binding.kind == "node":
                validate_node_tool_entry(entry, name, line=None, column=None)
            else:
                validate_python_tool_entry(entry, name, line=None, column=None)
        except Namel3ssError as err:
            invalid.append(name)
            issues.append(
                ToolIssue(
                    code="tools.invalid_binding",
                    message=str(err),
                    severity="error",
                    tool_name=name,
                )
            )
    return sorted(set(invalid)), issues


def _find_runner_issues(
    bindings: dict[str, ToolBinding],
    config,
) -> tuple[list[str], list[str], list[str], list[str], list[ToolIssue]]:
    invalid_runners: list[str] = []
    missing_urls: list[str] = []
    missing_images: list[str] = []
    missing_runtime: list[str] = []
    issues: list[ToolIssue] = []
    runtime = detect_container_runtime()
    for name, binding in bindings.items():
        runner = binding.runner
        if runner is None:
            continue
        allowed = _allowed_runners(binding)
        if runner not in allowed:
            invalid_runners.append(name)
            issues.append(
                ToolIssue(
                    code="tools.invalid_runner",
                    message=_invalid_runner_message(name, allowed),
                    severity="error",
                    tool_name=name,
                )
            )
            continue
        if runner == "service":
            if not (binding.url or config.python_tools.service_url):
                missing_urls.append(name)
                issues.append(
                    ToolIssue(
                        code="tools.service_url_missing",
                        message=_missing_service_url_message(name),
                        severity="error",
                        tool_name=name,
                    )
                )
        if runner == "container":
            if not binding.image:
                missing_images.append(name)
                issues.append(
                    ToolIssue(
                        code="tools.container_image_missing",
                        message=_missing_container_image_message(name),
                        severity="error",
                        tool_name=name,
                    )
                )
            if runtime is None:
                missing_runtime.append(name)
                issues.append(
                    ToolIssue(
                        code="tools.container_runtime_missing",
                        message=_missing_container_runtime_message(name),
                        severity="error",
                        tool_name=name,
                    )
                )
    return (
        sorted(set(invalid_runners)),
        sorted(set(missing_urls)),
        sorted(set(missing_images)),
        sorted(set(missing_runtime)),
        issues,
    )


def _find_empty_io(declared_tools: list[ToolDeclInfo]) -> tuple[list[str], list[ToolIssue]]:
    empty: list[str] = []
    issues: list[ToolIssue] = []
    for tool in declared_tools:
        missing_sections = []
        if tool.input_fields == 0:
            missing_sections.append("input")
        if tool.output_fields == 0:
            missing_sections.append("output")
        if not missing_sections:
            continue
        empty.append(tool.name)
        issues.append(
            ToolIssue(
                code="tools.missing_io",
                message=_missing_io_message(tool.name, missing_sections),
                severity="warning",
                tool_name=tool.name,
                line=tool.line,
                column=tool.column,
            )
        )
    return sorted(set(empty)), issues


def _line_for_tool(declared_map: dict[str, ToolDeclInfo], name: str) -> int | None:
    tool = declared_map.get(name)
    return tool.line if tool else None


def _column_for_tool(declared_map: dict[str, ToolDeclInfo], name: str) -> int | None:
    tool = declared_map.get(name)
    return tool.column if tool else None


def _missing_binding_message(tool_name: str) -> str:
    slug = slugify_tool_name(tool_name)
    return build_guidance_message(
        what=f'Tool "{tool_name}" is missing a binding.',
        why="The tool is declared but no entry exists in .namel3ss/tools.yaml.",
        fix=(
            "Run `n3 tools bind --auto` or bind it manually with "
            f'`n3 tools bind "{tool_name}" --entry "tools.{slug}:run"`.'
        ),
        example="n3 tools bind --auto",
    )


def _unused_binding_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'Binding for "{tool_name}" is unused.',
        why="The tool is bound in .namel3ss/tools.yaml but not declared in app.ai.",
        fix="Remove the binding or declare the tool.",
        example=f'n3 tools unbind "{tool_name}"',
    )


def _collision_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'Tool "{tool_name}" collides with a tool pack.',
        why="Pack tools have priority, so custom bindings with the same name are ignored.",
        fix="Rename the tool or disable the pack before binding.",
        example=f'n3 tools unbind "{tool_name}"',
    )


def _invalid_binding_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'Tool "{tool_name}" binding is invalid.',
        why="Bindings must be valid module:function entries.",
        fix="Update the binding entry to a valid module:function path.",
        example=f'n3 tools bind "{tool_name}" --entry "tools.my_tool:run"',
    )


def _missing_io_message(tool_name: str, sections: list[str]) -> str:
    missing = " and ".join(sections)
    return build_guidance_message(
        what=f'Tool "{tool_name}" has an empty {missing} section.',
        why="Tool input/output fields are used for schema validation.",
        fix="Add the missing fields or remove the empty section.",
        example=_tool_decl_example(tool_name),
    )


def _duplicate_decl_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'Duplicate tool declaration for "{tool_name}".',
        why="Tool names must be unique.",
        fix="Rename or remove the duplicate declaration.",
        example=_tool_decl_example(tool_name),
    )


def _tool_decl_example(tool_name: str) -> str:
    return (
        f'tool "{tool_name}":\n'
        "  implemented using python\n\n"
        "  input:\n"
        "    name is text\n\n"
        "  output:\n"
        "    result is json"
    )


def _allowed_runners(binding: ToolBinding) -> tuple[str, ...]:
    if binding.kind == "node":
        return ("node", "service")
    return ("local", "service", "container")


def _invalid_runner_message(tool_name: str, allowed: tuple[str, ...]) -> str:
    example = 'runner: "node"' if "node" in allowed else 'runner: "local"'
    return build_guidance_message(
        what=f'Tool "{tool_name}" has an invalid runner.',
        why=f"Runner must be one of: {', '.join(allowed)}.",
        fix="Update the runner field or remove it.",
        example=example,
    )


def _missing_service_url_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'Tool "{tool_name}" requires a service URL.',
        why="Runner is set to service but no URL is configured.",
        fix="Set url in tools.yaml or define N3_TOOL_SERVICE_URL.",
        example='N3_TOOL_SERVICE_URL=http://127.0.0.1:8787/tools',
    )


def _missing_container_image_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'Tool "{tool_name}" requires a container image.',
        why="Runner is set to container but image is missing.",
        fix="Set image in tools.yaml.",
        example='image: "ghcr.io/namel3ss/tools:latest"',
    )


def _missing_container_runtime_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'Tool "{tool_name}" requires a container runtime.',
        why="Runner is set to container but docker/podman was not found.",
        fix="Install docker/podman or switch to a different runner.",
        example='n3 tools set-runner "tool name" --runner local',
    )


__all__ = ["analyze_tool_health"]
