from __future__ import annotations

from pathlib import Path, PurePosixPath

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.backend import studio_effect_adapter
from namel3ss.runtime.persistence_paths import resolve_persistence_root, resolve_project_root
from namel3ss.runtime.tools.schema_validate import validate_tool_fields
from namel3ss.utils.slugify import slugify_text


ALLOWED_INPUT_FIELDS = {"operation", "path", "content"}
ALLOWED_OUTPUT_FIELDS = {"content", "ok", "bytes"}


def execute_file_tool(
    ctx,
    tool: ir.ToolDecl,
    payload: object,
    *,
    line: int | None,
    column: int | None,
) -> dict:
    _validate_file_tool_schema(tool, line=line, column=column)
    validate_tool_fields(
        fields=tool.input_fields,
        payload=payload,
        tool_name=tool.name,
        phase="input",
        line=line,
        column=column,
        type_mode="tool",
        expect_object=True,
    )
    if not isinstance(payload, dict):
        raise Namel3ssError("File tool input must be an object", line=line, column=column)
    operation = _read_operation(payload, line=line, column=column)
    rel_path = _read_path(payload, line=line, column=column)
    content = payload.get("content")
    if operation == "write" and not isinstance(content, str):
        raise Namel3ssError("File write content must be text", line=line, column=column)
    root = _file_root(ctx)
    scoped_path = _resolve_scoped_path(root, rel_path, line=line, column=column)
    display_path = f"{_scope_name(ctx.project_root, ctx.app_path)}/{rel_path}"
    trace_event = studio_effect_adapter.record_file_operation(
        ctx,
        tool_name=tool.name,
        operation=operation,
        path=display_path,
        content=content if operation == "write" else None,
    )
    try:
        if operation == "read":
            text = _read_file(scoped_path, line=line, column=column)
            output = _build_output(tool, content=text, bytes_len=len(text.encode("utf-8")))
            studio_effect_adapter.record_file_result(trace_event, content=text, ok=True)
        else:
            bytes_len = _write_file(scoped_path, content or "")
            output = _build_output(tool, content=None, bytes_len=bytes_len)
            studio_effect_adapter.record_file_result(trace_event, ok=True)
    except Exception as err:
        studio_effect_adapter.record_file_error(trace_event, message=str(err))
        raise
    validate_tool_fields(
        fields=tool.output_fields,
        payload=output,
        tool_name=tool.name,
        phase="output",
        line=line,
        column=column,
        type_mode="tool",
        expect_object=True,
    )
    return output


def _file_root(ctx) -> Path:
    root = resolve_persistence_root(ctx.project_root, ctx.app_path, allow_create=True)
    if root is None:
        raise Namel3ssError("Unable to resolve file storage root")
    scope = _scope_name(ctx.project_root, ctx.app_path)
    return root / ".namel3ss" / "files" / scope


def _scope_name(project_root: str | Path | None, app_path: str | Path | None) -> str:
    if app_path:
        app_path = Path(app_path)
        root = resolve_project_root(project_root, app_path)
        if root:
            try:
                rel = app_path.resolve().relative_to(root.resolve())
                return slugify_text(rel.as_posix())
            except Exception:
                pass
        return slugify_text(app_path.name)
    return "app"


def _resolve_scoped_path(root: Path, rel_path: str, *, line: int | None, column: int | None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    parts = PurePosixPath(rel_path).parts
    safe = Path(*parts)
    target = root / safe
    if not str(target.resolve()).startswith(str(root.resolve())):
        raise Namel3ssError("File path must stay within the app file scope", line=line, column=column)
    return target


def _read_operation(payload: dict, *, line: int | None, column: int | None) -> str:
    value = payload.get("operation")
    if not isinstance(value, str):
        raise Namel3ssError("File operation must be text", line=line, column=column)
    operation = value.strip().lower()
    if operation not in {"read", "write"}:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unsupported file operation '{operation}'.",
                why="Only read and write are supported.",
                fix='Use "read" or "write".',
                example='operation is "read"',
            ),
            line=line,
            column=column,
        )
    return operation


def _read_path(payload: dict, *, line: int | None, column: int | None) -> str:
    value = payload.get("path")
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError("File path must be a non-empty string", line=line, column=column)
    path = PurePosixPath(value.strip())
    if path.is_absolute() or ".." in path.parts:
        raise Namel3ssError("File path must be relative to the app file scope", line=line, column=column)
    return path.as_posix()


def _read_file(path: Path, *, line: int | None, column: int | None) -> str:
    if not path.exists():
        raise Namel3ssError("File does not exist", line=line, column=column)
    return path.read_text(encoding="utf-8")


def _write_file(path: Path, content: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return len(content.encode("utf-8"))


def _build_output(tool: ir.ToolDecl, *, content: str | None, bytes_len: int) -> dict:
    available: dict[str, object] = {"ok": True, "bytes": bytes_len}
    if content is not None:
        available["content"] = content
    output: dict[str, object] = {}
    for field in tool.output_fields:
        if field.name not in ALLOWED_OUTPUT_FIELDS:
            raise Namel3ssError(_invalid_output_field_message(tool.name))
        if field.name not in available:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'File tool "{tool.name}" cannot provide "{field.name}" for this operation.',
                    why="Read operations return content; write operations return ok/bytes.",
                    fix="Align the output fields with the operation.",
                    example='output:\n  ok is boolean\n  bytes is number',
                ),
                line=field.line,
                column=field.column,
            )
        output[field.name] = available[field.name]
    return output


def _validate_file_tool_schema(tool: ir.ToolDecl, *, line: int | None, column: int | None) -> None:
    input_fields = {field.name: field for field in tool.input_fields}
    output_fields = {field.name: field for field in tool.output_fields}
    _require_field(input_fields, "operation", tool.name, line=line, column=column)
    _require_field(input_fields, "path", tool.name, line=line, column=column)
    _require_type(input_fields, "operation", "text", tool.name, line=line, column=column)
    _require_type(input_fields, "path", "text", tool.name, line=line, column=column)
    _require_type_optional(input_fields, "content", "text", tool.name, line=line, column=column)
    for field in input_fields.values():
        if field.name not in ALLOWED_INPUT_FIELDS:
            raise Namel3ssError(_invalid_input_field_message(tool.name), line=line, column=column)
    for field in output_fields.values():
        if field.name not in ALLOWED_OUTPUT_FIELDS:
            raise Namel3ssError(_invalid_output_field_message(tool.name), line=line, column=column)
    _require_type_optional(output_fields, "content", "text", tool.name, line=line, column=column)
    _require_type_optional(output_fields, "ok", "boolean", tool.name, line=line, column=column)
    _require_type_optional(output_fields, "bytes", "number", tool.name, line=line, column=column)


def _require_field(
    fields: dict[str, ir.ToolField],
    name: str,
    tool_name: str,
    *,
    line: int | None,
    column: int | None,
) -> None:
    if name in fields:
        return
    raise Namel3ssError(
        build_guidance_message(
            what=f'File tool "{tool_name}" is missing "{name}" input.',
            why="File tools must declare operation and path.",
            fix=f'Add `{name} is text` to the input block.',
            example='input:\n  operation is text\n  path is text',
        ),
        line=line,
        column=column,
    )


def _require_type(
    fields: dict[str, ir.ToolField],
    name: str,
    expected: str,
    tool_name: str,
    *,
    line: int | None,
    column: int | None,
) -> None:
    field = fields.get(name)
    if not field:
        return
    if field.type_name != expected:
        raise Namel3ssError(
            build_guidance_message(
                what=f'File tool "{tool_name}" input "{name}" must be {expected}.',
                why=f"The tool declares {name} as {field.type_name}.",
                fix=f"Update {name} to {expected}.",
                example=f'input:\n  {name} is {expected}',
            ),
            line=line,
            column=column,
        )


def _require_type_optional(
    fields: dict[str, ir.ToolField],
    name: str,
    expected: str,
    tool_name: str,
    *,
    line: int | None,
    column: int | None,
) -> None:
    if name not in fields:
        return
    _require_type(fields, name, expected, tool_name, line=line, column=column)


def _invalid_input_field_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'File tool "{tool_name}" has unsupported input fields.',
        why="File tools only support operation, path, and content.",
        fix="Remove unsupported input fields.",
        example='input:\n  operation is text\n  path is text',
    )


def _invalid_output_field_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'File tool "{tool_name}" has unsupported output fields.',
        why="File tools only support content, ok, and bytes outputs.",
        fix="Remove unsupported output fields.",
        example='output:\n  content is text',
    )


__all__ = ["execute_file_tool"]
