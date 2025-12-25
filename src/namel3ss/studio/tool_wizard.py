from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.core import parse
from namel3ss.ir.nodes import lower_program
from namel3ss.runtime.tools.bindings import load_tool_bindings, write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.templates.tools import SUPPORTED_FIELD_TYPES, ToolField, render_tool_decl, render_tool_module
from namel3ss.utils.slugify import slugify_tool_name


_TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_. ]*$")
_FIELD_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_. ]*$")


@dataclass(frozen=True)
class ToolWizardRequest:
    tool_name: str
    purity: str
    timeout_seconds: int | None
    input_fields: list[ToolField]
    output_fields: list[ToolField]
    preview: bool
    reuse_existing: bool


def run_tool_wizard(app_path: Path, payload: dict) -> dict:
    request = _parse_request(payload)
    app_path = app_path.resolve()
    app_root = app_path.parent
    tool_names = _read_tool_names(app_path)
    tool_dir = app_root / "tools"
    slug = slugify_tool_name(request.tool_name)
    module_path = _module_file_path(tool_dir, slug)
    bindings = load_tool_bindings(app_root)
    conflicts = _detect_conflicts(tool_names, bindings, module_path, request.tool_name)
    preview_payload = _build_preview_payload(request, module_path, slug, bindings, tool_names)
    if request.preview:
        suggestion = _suggest_names(tool_names | set(bindings.keys()), tool_dir, request.tool_name) if conflicts else None
        return {
            "ok": True,
            "status": "preview",
            "preview": preview_payload,
            "conflicts": conflicts,
            "suggested": suggestion,
        }
    if conflicts and not request.reuse_existing:
        suggestion = _suggest_names(tool_names | set(bindings.keys()), tool_dir, request.tool_name)
        return {
            "ok": False,
            "status": "conflict",
            "conflicts": conflicts,
            "message": "Tool name or module already exists.",
            "suggested": suggestion,
            "preview": preview_payload,
        }
    if request.tool_name not in tool_names:
        tool_block = render_tool_decl(
            tool_name=request.tool_name,
            purity=request.purity,
            timeout_seconds=request.timeout_seconds,
            input_fields=request.input_fields,
            output_fields=request.output_fields,
        )
        updated_source = _append_tool_block(app_path.read_text(encoding="utf-8"), tool_block)
        app_path.write_text(updated_source, encoding="utf-8")
    if not module_path.exists():
        module_path.parent.mkdir(parents=True, exist_ok=True)
        module_path.write_text(preview_payload["stub"]["content"], encoding="utf-8")
    bindings.setdefault(
        request.tool_name,
        ToolBinding(
            kind="python",
            entry=f"tools.{slug}:run",
        ),
    )
    write_tool_bindings(app_root, bindings)
    return {
        "ok": True,
        "tool_name": request.tool_name,
        "entry": f"tools.{slug}:run",
        "tool_path": str(module_path),
        "app_path": str(app_path),
    }


def _parse_request(payload: dict) -> ToolWizardRequest:
    if not isinstance(payload, dict):
        raise Namel3ssError(_wizard_error("Tool wizard payload must be an object."))
    tool_name = _require_text(payload, "tool_name")
    purity = _require_text(payload, "purity").lower()
    timeout_seconds = _read_timeout(payload.get("timeout_seconds"))
    _validate_tool_name(tool_name)
    preview = bool(payload.get("preview", False))
    reuse_existing = bool(payload.get("reuse_existing", False))
    module_name = payload.get("module_name")
    function_name = payload.get("function_name")
    slug = slugify_tool_name(tool_name)
    if module_name and module_name != slug:
        raise Namel3ssError(_wizard_error("Module name must match the tool slug for auto-binding."))
    if function_name and function_name != "run":
        raise Namel3ssError(_wizard_error("Function name must be 'run' for auto-binding."))
    if purity not in {"pure", "impure"}:
        raise Namel3ssError(_wizard_error("purity must be 'pure' or 'impure'."))
    input_fields = _parse_fields(payload.get("input_fields", ""))
    output_fields = _parse_fields(payload.get("output_fields", ""))
    return ToolWizardRequest(
        tool_name=tool_name,
        purity=purity,
        timeout_seconds=timeout_seconds,
        input_fields=input_fields,
        output_fields=output_fields,
        preview=preview,
        reuse_existing=reuse_existing,
    )


def _parse_fields(raw: object) -> list[ToolField]:
    if raw is None:
        return []
    if not isinstance(raw, str):
        raise Namel3ssError(_wizard_error("Field definitions must be a string."))
    fields: list[ToolField] = []
    for idx, line in enumerate(raw.splitlines(), start=1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if ":" not in text:
            raise Namel3ssError(_wizard_error(f"Line {idx}: expected name:type."))
        name_part, type_part = text.split(":", 1)
        name = name_part.strip()
        field_type = type_part.strip().lower()
        required = True
        if name.endswith("?"):
            required = False
            name = name[:-1]
        name = name.strip()
        if not name or not _FIELD_NAME_PATTERN.match(name):
            raise Namel3ssError(
                _wizard_error(f"Line {idx}: field name must use letters, numbers, spaces, underscores, or dots.")
            )
        if field_type not in SUPPORTED_FIELD_TYPES:
            raise Namel3ssError(_wizard_error(f"Line {idx}: type must be one of {sorted(SUPPORTED_FIELD_TYPES)}."))
        fields.append(ToolField(name=name, field_type=field_type, required=required))
    return fields


def _read_tool_names(app_path: Path) -> set[str]:
    try:
        source = app_path.read_text(encoding="utf-8")
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Unable to read app.ai for tool wizard.",
                why=str(err),
                fix="Ensure app.ai is readable and try again.",
                example="n3 app.ai check",
            )
        ) from err
    try:
        program = lower_program(parse(source))
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Unable to parse app.ai before inserting a tool.",
                why=str(err).splitlines()[0],
                fix="Fix the parse error before using the tool wizard.",
                example="n3 app.ai check",
            )
        ) from err
    return set(program.tools.keys())


def _detect_conflicts(tool_names: set[str], bindings: dict[str, ToolBinding], module_path: Path, tool_name: str) -> list[str]:
    conflicts = []
    if tool_name in tool_names:
        conflicts.append("tool_name")
    if tool_name in bindings:
        conflicts.append("tool_binding")
    if module_path.exists():
        conflicts.append("tool_module")
    return conflicts


def _suggest_names(
    tool_names: set[str],
    tool_dir: Path,
    tool_name: str,
) -> dict:
    suggested_tool = _suggest_unique(tool_name, tool_names)
    suggested_slug = slugify_tool_name(suggested_tool)
    suggested_module = _suggest_unique_module(suggested_slug, tool_dir)
    return {
        "tool_name": suggested_tool,
        "entry": f"tools.{suggested_module}:run",
    }


def _suggest_unique(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    counter = 2
    while f"{base}_{counter}" in existing:
        counter += 1
    return f"{base}_{counter}"


def _suggest_unique_module(base: str, tool_dir: Path) -> str:
    candidate = base
    counter = 2
    while _module_file_path(tool_dir, candidate).exists():
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def _module_file_path(tool_dir: Path, module_name: str) -> Path:
    parts = module_name.split(".")
    return tool_dir.joinpath(*parts).with_suffix(".py")


def _build_preview_payload(
    request: ToolWizardRequest,
    module_path: Path,
    slug: str,
    bindings: dict[str, ToolBinding],
    tool_names: set[str],
) -> dict:
    module_content = render_tool_module(
        tool_name=request.tool_name,
        function_name="run",
        input_fields=request.input_fields,
        output_fields=request.output_fields,
    )
    tool_block = render_tool_decl(
        tool_name=request.tool_name,
        purity=request.purity,
        timeout_seconds=request.timeout_seconds,
        input_fields=request.input_fields,
        output_fields=request.output_fields,
    )
    binding_entry = bindings.get(request.tool_name)
    return {
        "tool_name": request.tool_name,
        "tool_decl_exists": request.tool_name in tool_names,
        "tool_block": tool_block,
        "binding": {
            "entry": binding_entry.entry if binding_entry else f"tools.{slug}:run",
            "exists": binding_entry is not None,
        },
        "stub": {
            "path": str(module_path),
            "exists": module_path.exists(),
            "content": module_content,
        },
    }


def _append_tool_block(source: str, block: str) -> str:
    stripped = source.rstrip("\n")
    if not stripped:
        return f"{block}\n"
    return f"{stripped}\n\n{block}\n"


def _require_text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(_wizard_error(f"{key} must be a non-empty string."))
    return value.strip()


def _validate_tool_name(name: str) -> None:
    if not _TOOL_NAME_PATTERN.match(name):
        raise Namel3ssError(_wizard_error("tool_name must be letters, numbers, spaces, underscores, or dots."))


def _read_timeout(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise Namel3ssError(_wizard_error("timeout_seconds must be a number."))
    try:
        parsed = int(float(value))
    except (TypeError, ValueError) as err:
        raise Namel3ssError(_wizard_error("timeout_seconds must be a number.")) from err
    if parsed <= 0:
        raise Namel3ssError(_wizard_error("timeout_seconds must be positive."))
    return parsed


def _wizard_error(message: str) -> str:
    return build_guidance_message(
        what="Tool wizard input is invalid.",
        why=message,
        fix="Update the wizard fields and try again.",
        example="tool_name = greeter",
    )


__all__ = ["ToolWizardRequest", "run_tool_wizard"]
