from __future__ import annotations

import sys
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


def generate_c_project(plan: NumericFlowPlan, out_root: Path) -> GeneratedProject:
    flow_slug = _slug(plan.flow_name)
    root = out_root / plan.flow_name / "c"
    source_path = root / f"{flow_slug}.c"
    header_path = root / "namel3ss.h"
    makefile_path = root / "Makefile"
    readme_path = root / "README.md"
    artifact_path, build_cmd = _artifact_and_command(flow_slug)

    files = {
        source_path: _render_c_source(plan, flow_slug),
        header_path: _render_header(flow_slug),
        makefile_path: _render_makefile(flow_slug, artifact_path.name),
        readme_path: _render_readme(flow_slug, artifact_path.name),
    }
    _write_files(files)

    return GeneratedProject(
        flow_name=plan.flow_name,
        language="c",
        root=root,
        artifact=root / artifact_path,
        header=header_path,
        files=tuple(sorted(files.keys(), key=lambda item: item.as_posix())),
        build_command=tuple(build_cmd),
    )


def _artifact_and_command(flow_slug: str) -> tuple[Path, list[str]]:
    if sys.platform.startswith("win"):
        artifact = Path(f"{flow_slug}.dll")
        cmd = [
            "cc",
            "-shared",
            "-o",
            artifact.as_posix(),
            f"{flow_slug}.c",
        ]
        return artifact, cmd
    if sys.platform == "darwin":
        artifact = Path(f"lib{flow_slug}.dylib")
        cmd = [
            "cc",
            "-dynamiclib",
            "-O2",
            "-fPIC",
            "-o",
            artifact.as_posix(),
            f"{flow_slug}.c",
        ]
        return artifact, cmd
    artifact = Path(f"lib{flow_slug}.so")
    cmd = [
        "cc",
        "-shared",
        "-O2",
        "-fPIC",
        "-o",
        artifact.as_posix(),
        f"{flow_slug}.c",
    ]
    return artifact, cmd


def _render_c_source(plan: NumericFlowPlan, flow_slug: str) -> str:
    lines: list[str] = []
    lines.extend(
        [
            '#include "namel3ss.h"',
            "",
            "#include <ctype.h>",
            "#include <stdio.h>",
            "#include <stdlib.h>",
            "#include <string.h>",
            "",
            "static int n3_set_error(char **error_json, const char *message) {",
            "  if (error_json == NULL) {",
            "    return 1;",
            "  }",
            "  const char *prefix = \"{\\\"error\\\":\\\"\";",
            "  const char *suffix = \"\\\"}\";",
            "  size_t size = strlen(prefix) + strlen(message) + strlen(suffix) + 1;",
            "  char *buffer = (char *)malloc(size);",
            "  if (buffer == NULL) {",
            "    return 1;",
            "  }",
            "  (void)snprintf(buffer, size, \"%s%s%s\", prefix, message, suffix);",
            "  *error_json = buffer;",
            "  return 1;",
            "}",
            "",
            "static const char *n3_find_key(const char *json, const char *key) {",
            "  size_t key_len = strlen(key);",
            "  const char *cursor = json;",
            "  while ((cursor = strchr(cursor, '\"')) != NULL) {",
            "    cursor += 1;",
            "    if (strncmp(cursor, key, key_len) != 0) {",
            "      continue;",
            "    }",
            "    if (cursor[key_len] != '\"') {",
            "      continue;",
            "    }",
            "    return cursor + key_len + 1;",
            "  }",
            "  return NULL;",
            "}",
            "",
            "static int n3_extract_number(const char *json, const char *key, double *out) {",
            "  if (json == NULL || key == NULL || out == NULL) {",
            "    return 0;",
            "  }",
            "  const char *cursor = n3_find_key(json, key);",
            "  if (cursor == NULL) {",
            "    return 0;",
            "  }",
            "  cursor = strchr(cursor, ':');",
            "  if (cursor == NULL) {",
            "    return 0;",
            "  }",
            "  cursor += 1;",
            "  while (*cursor != '\\0' && isspace((unsigned char)*cursor)) {",
            "    cursor += 1;",
            "  }",
            "  char *end = NULL;",
            "  double value = strtod(cursor, &end);",
            "  if (end == cursor) {",
            "    return 0;",
            "  }",
            "  *out = value;",
            "  return 1;",
            "}",
            "",
            "int run_flow(const char *input_json, char **output_json, char **error_json) {",
            "  if (output_json == NULL || error_json == NULL) {",
            "    return 1;",
            "  }",
            "  *output_json = NULL;",
            "  *error_json = NULL;",
            "  if (input_json == NULL) {",
            "    input_json = \"{}\";",
            "  }",
        ]
    )

    for key in plan.input_keys:
        name = _var_name(key)
        lines.extend(
            [
                f"  double input_{name} = 0.0;",
                f"  if (!n3_extract_number(input_json, \"{_escape_c_string(key)}\", &input_{name})) {{",
                f"    return n3_set_error(error_json, \"missing_or_invalid_input_{_escape_c_string(key)}\");",
                "  }",
            ]
        )

    lines.append("")
    for assignment in plan.assignments:
        lines.append(f"  double local_{_var_name(assignment.name)} = {_emit_expr(assignment.expr)};")
    lines.append("")
    lines.append(f"  double result = {_emit_expr(plan.result)};")
    lines.extend(
        [
            "  int size = snprintf(NULL, 0, \"{\\\"result\\\":%.17g}\", result);",
            "  if (size < 0) {",
            "    return n3_set_error(error_json, \"format_failed\");",
            "  }",
            "  char *buffer = (char *)malloc((size_t)size + 1);",
            "  if (buffer == NULL) {",
            "    return n3_set_error(error_json, \"out_of_memory\");",
            "  }",
            "  (void)snprintf(buffer, (size_t)size + 1, \"{\\\"result\\\":%.17g}\", result);",
            "  *output_json = buffer;",
            "  return 0;",
            "}",
            "",
            "void free_json_string(char *ptr) {",
            "  if (ptr != NULL) {",
            "    free(ptr);",
            "  }",
            "}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_header(flow_slug: str) -> str:
    guard = f"NAMELESS_COMPILED_{flow_slug.upper()}_H"
    return (
        f"#ifndef {guard}\n"
        f"#define {guard}\n"
        "\n"
        "#ifdef __cplusplus\n"
        'extern \"C\" {\n'
        "#endif\n"
        "\n"
        "int run_flow(const char *input_json, char **output_json, char **error_json);\n"
        "void free_json_string(char *ptr);\n"
        "\n"
        "#ifdef __cplusplus\n"
        "}\n"
        "#endif\n"
        "\n"
        f"#endif /* {guard} */\n"
    )


def _render_makefile(flow_slug: str, artifact_name: str) -> str:
    return (
        f"FLOW={flow_slug}\n"
        f"ARTIFACT={artifact_name}\n"
        "\n"
        "all:\n"
        "\tcc -shared -O2 -fPIC -o $(ARTIFACT) $(FLOW).c\n"
        "\n"
        "clean:\n"
        "\trm -f $(ARTIFACT)\n"
    )


def _render_readme(flow_slug: str, artifact_name: str) -> str:
    return (
        f"# Compiled Flow {flow_slug}\n"
        "\n"
        "This project exposes a stable C ABI:\n"
        "\n"
        "- `int run_flow(const char *input_json, char **output_json, char **error_json)`\n"
        "- `void free_json_string(char *ptr)`\n"
        "\n"
        "Build with:\n"
        "\n"
        "```bash\n"
        "make\n"
        "```\n"
        "\n"
        f"The shared library is written to `{artifact_name}`.\n"
    )


def _emit_expr(expr: NumericExpr) -> str:
    if isinstance(expr, NumberLiteral):
        return expr.text
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
    parts = []
    for ch in name:
        if ch.isalnum() or ch == "_":
            parts.append(ch.lower())
        else:
            parts.append("_")
    slug = "".join(parts).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    if not slug:
        slug = "flow"
    if slug[0].isdigit():
        slug = f"flow_{slug}"
    return slug


def _var_name(name: str) -> str:
    return _slug(name)


def _escape_c_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


__all__ = ["generate_c_project"]
