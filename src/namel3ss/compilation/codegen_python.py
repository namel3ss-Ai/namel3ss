from __future__ import annotations

from pathlib import Path

from namel3ss.compilation.model import (
    BinaryNumber,
    GeneratedProject,
    InputNumber,
    LocalNumber,
    NumberLiteral,
    NumericExpr,
    NumericFlowPlan,
    UnaryNumber,
)


def generate_python_project(plan: NumericFlowPlan, out_root: Path) -> GeneratedProject:
    flow_slug = _slug(plan.flow_name)
    root = out_root / plan.flow_name / "python"
    module_path = root / f"{flow_slug}_compiled.py"
    readme_path = root / "README.md"

    files = {
        module_path: _render_python_module(plan),
        readme_path: _render_readme(flow_slug),
    }
    _write_files(files)

    return GeneratedProject(
        flow_name=plan.flow_name,
        language="python",
        root=root,
        artifact=module_path,
        header=None,
        files=tuple(sorted(files.keys(), key=lambda item: item.as_posix())),
        build_command=None,
    )


def _render_python_module(plan: NumericFlowPlan) -> str:
    lines: list[str] = [
        "from __future__ import annotations",
        "",
        "import json",
        "import math",
        "from typing import Any",
        "",
        "",
        "def _require_input_object(input_json: str | None) -> dict[str, Any]:",
        "    if input_json is None or input_json == \"\":",
        "        return {}",
        "    payload = json.loads(input_json)",
        "    if not isinstance(payload, dict):",
        "        raise ValueError(\"input_must_be_object\")",
        "    return payload",
        "",
        "",
        "def _require_number(payload: dict[str, Any], key: str) -> float:",
        "    if key not in payload:",
        "        raise ValueError(f\"missing_or_invalid_input_{key}\")",
        "    value = payload[key]",
        "    if isinstance(value, bool) or not isinstance(value, (int, float)):",
        "        raise ValueError(f\"missing_or_invalid_input_{key}\")",
        "    number = float(value)",
        "    if not math.isfinite(number):",
        "        raise ValueError(f\"missing_or_invalid_input_{key}\")",
        "    return number",
        "",
        "",
        "def run_flow(input_json: str | None) -> str:",
        "    payload = _require_input_object(input_json)",
    ]

    for key in plan.input_keys:
        lines.append(f"    input_{_var_name(key)} = _require_number(payload, \"{_escape_python_string(key)}\")")
    if plan.input_keys:
        lines.append("")

    for assignment in plan.assignments:
        lines.append(f"    local_{_var_name(assignment.name)} = {_emit_expr(assignment.expr)}")
    if plan.assignments:
        lines.append("")

    lines.extend(
        [
            f"    result = {_emit_expr(plan.result)}",
            "    if not math.isfinite(result):",
            "        raise ValueError(\"result_not_finite\")",
            "    return json.dumps({\"result\": result}, separators=(\",\", \":\"), sort_keys=True)",
            "",
            "",
            "def run_flow_safe(input_json: str | None) -> tuple[bool, str]:",
            "    try:",
            "        return True, run_flow(input_json)",
            "    except json.JSONDecodeError:",
            "        return False, json.dumps({\"error\": \"invalid_json\"}, separators=(\",\", \":\"), sort_keys=True)",
            "    except ValueError as err:",
            "        return False, json.dumps({\"error\": str(err)}, separators=(\",\", \":\"), sort_keys=True)",
            "",
            "",
            "if __name__ == \"__main__\":",
            "    import sys",
            "",
            "    raw_input = sys.argv[1] if len(sys.argv) > 1 else \"{}\"",
            "    ok, payload = run_flow_safe(raw_input)",
            "    if ok:",
            "        print(payload)",
            "    else:",
            "        print(payload, file=sys.stderr)",
            "        raise SystemExit(1)",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def _render_readme(flow_slug: str) -> str:
    return (
        f"# Compiled Flow {flow_slug} (python)\n"
        "\n"
        "This project contains an ahead-of-time Python module with deterministic execution.\n"
        "\n"
        "Exports:\n"
        "\n"
        "- `run_flow(input_json)` returns deterministic JSON output.\n"
        "- `run_flow_safe(input_json)` returns `(ok, payload)` with error JSON on failure.\n"
    )


def _emit_expr(expr: NumericExpr) -> str:
    if isinstance(expr, NumberLiteral):
        return f"float({expr.text})"
    if isinstance(expr, InputNumber):
        return f"input_{_var_name(expr.key)}"
    if isinstance(expr, LocalNumber):
        return f"local_{_var_name(expr.name)}"
    if isinstance(expr, UnaryNumber):
        return f"({expr.op}{_emit_expr(expr.operand)})"
    if isinstance(expr, BinaryNumber):
        return f"({_emit_expr(expr.left)} {expr.op} {_emit_expr(expr.right)})"
    raise ValueError(f"Unsupported numeric expr: {expr}")


def _write_files(files: dict[Path, str]) -> None:
    for path in sorted(files.keys(), key=lambda item: item.as_posix()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[path], encoding="utf-8")


def _slug(name: str) -> str:
    chars = []
    for ch in name:
        if ch.isalnum() or ch == "_":
            chars.append(ch.lower())
        else:
            chars.append("_")
    text = "".join(chars).strip("_")
    while "__" in text:
        text = text.replace("__", "_")
    if not text:
        text = "flow"
    if text[0].isdigit():
        text = f"flow_{text}"
    return text


def _var_name(name: str) -> str:
    return _slug(name)


def _escape_python_string(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


__all__ = ["generate_python_project"]
