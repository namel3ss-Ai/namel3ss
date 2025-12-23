from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.specs import parse_source_spec
from namel3ss.pkg.types import DependencySpec, Manifest
from namel3ss.pkg.versions import parse_constraint, parse_semver


MANIFEST_FILENAME = "namel3ss.toml"


def load_manifest(root: Path) -> Manifest:
    path = root / MANIFEST_FILENAME
    if not path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Dependency manifest not found at {path.as_posix()}.",
                why="Packages are declared in namel3ss.toml.",
                fix="Create namel3ss.toml or run `n3 pkg add`.",
                example="[dependencies]\\ninventory = \"github:owner/repo@v0.1.0\"",
            )
        )
    data = _parse_toml(path.read_text(encoding="utf-8"), path)
    deps = data.get("dependencies", {})
    if deps is None:
        deps = {}
    if not isinstance(deps, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="Dependencies section is not a table.",
                why="Dependencies must be a mapping of name to source.",
                fix="Use [dependencies] with name = \"github:owner/repo@ref\" entries.",
                example='[dependencies]\\ninventory = \"github:owner/repo@v0.1.0\"',
            )
        )
    parsed: Dict[str, DependencySpec] = {}
    for name, value in deps.items():
        parsed[name] = _parse_dependency(name, value)
    return Manifest(dependencies=parsed, path=path)


def load_manifest_optional(root: Path) -> Manifest:
    path = root / MANIFEST_FILENAME
    if not path.exists():
        return Manifest(dependencies={}, path=path)
    return load_manifest(root)


def write_manifest(root: Path, manifest: Manifest) -> Path:
    path = root / MANIFEST_FILENAME
    path.write_text(format_manifest(manifest), encoding="utf-8")
    return path


def format_manifest(manifest: Manifest) -> str:
    lines: List[str] = ["[dependencies]"]
    for name in sorted(manifest.dependencies.keys()):
        dep = manifest.dependencies[name]
        source = dep.source.as_string()
        if dep.constraint_raw:
            lines.append(f'{name} = {{ source = "{source}", version = "{dep.constraint_raw}" }}')
        else:
            lines.append(f'{name} = "{source}"')
    lines.append("")
    return "\n".join(lines)


def _parse_dependency(name: str, value: Any) -> DependencySpec:
    if isinstance(value, str):
        source = parse_source_spec(value)
        constraint = _constraint_from_ref(source.ref)
        return DependencySpec(name=name, source=source, constraint_raw=None, constraint=constraint)
    if isinstance(value, dict):
        source_value = value.get("source")
        version_value = value.get("version")
        if not isinstance(source_value, str):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Dependency '{name}' is missing a source.",
                    why="Each dependency must include a GitHub source.",
                    fix="Add a source field to the dependency.",
                    example=f'{name} = {{ source = "github:owner/repo@v0.1.0" }}',
                )
            )
        source = parse_source_spec(source_value)
        constraint = None
        if version_value is not None:
            if not isinstance(version_value, str):
                raise Namel3ssError(
                    build_guidance_message(
                        what=f"Dependency '{name}' has an invalid version constraint.",
                        why="Version constraints must be strings like ^0.1 or =0.1.2.",
                        fix="Use a valid version constraint string.",
                        example=f'{name} = {{ source = "github:owner/repo@v0.1.0", version = "^0.1" }}',
                    )
                )
            constraint = parse_constraint(version_value)
        return DependencySpec(name=name, source=source, constraint_raw=version_value, constraint=constraint)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Dependency '{name}' has an unsupported value.",
            why="Dependencies must be strings or inline tables.",
            fix="Use a GitHub source string or inline table.",
            example=f'{name} = "github:owner/repo@v0.1.0"',
        )
    )


def _constraint_from_ref(ref: str):
    try:
        version = parse_semver(ref)
    except Namel3ssError:
        return None
    return parse_constraint(f"={version}")


def _parse_toml(text: str, path: Path) -> Dict[str, Any]:
    try:
        import tomllib  # type: ignore
    except Exception:
        return _parse_toml_minimal(text, path)
    try:
        data = tomllib.loads(text)
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Dependency manifest is not valid TOML.",
                why=f"TOML parsing failed: {err}.",
                fix="Fix the TOML syntax in namel3ss.toml.",
                example='[dependencies]\\ninventory = "github:owner/repo@v0.1.0"',
            )
        ) from err
    if not isinstance(data, dict):
        return {}
    return data


def _parse_toml_minimal(text: str, path: Path) -> Dict[str, Any]:
    current = None
    data: Dict[str, Any] = {}
    line_num = 0
    for raw_line in text.splitlines():
        line_num += 1
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            data.setdefault(section, {})
            current = section
            continue
        if current is None:
            continue
        if "=" not in line:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Invalid line in {path.name}.",
                    why="Expected key = value inside a section.",
                    fix="Add a dependency entry under [dependencies].",
                    example='inventory = "github:owner/repo@v0.1.0"',
                ),
                line=line_num,
                column=1,
            )
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        data[current][key] = _parse_toml_value(value, line_num, path)
    return data


def _parse_toml_value(value: str, line_num: int, path: Path) -> Any:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("{") and value.endswith("}"):
        return _parse_inline_table(value, line_num, path)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unsupported value in {path.name}.",
            why="Only quoted strings and inline tables are supported.",
            fix="Wrap values in quotes or use inline tables.",
            example='inventory = { source = "github:owner/repo@v0.1.0" }',
        ),
        line=line_num,
        column=1,
    )


def _parse_inline_table(value: str, line_num: int, path: Path) -> Dict[str, Any]:
    inner = value[1:-1].strip()
    if not inner:
        return {}
    parts = _split_inline_parts(inner)
    table: Dict[str, Any] = {}
    for part in parts:
        if "=" not in part:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Inline table entry is invalid in {path.name}.",
                    why="Entries must be key = \"value\" pairs.",
                    fix="Add key/value pairs separated by commas.",
                    example='{ source = "github:owner/repo@v0.1.0", version = "^0.1" }',
                ),
                line=line_num,
                column=1,
            )
        key, raw_value = part.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not raw_value.startswith('"') or not raw_value.endswith('"'):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Inline table value is invalid in {path.name}.",
                    why="Inline table values must be quoted strings.",
                    fix="Wrap the value in double quotes.",
                    example='{ source = "github:owner/repo@v0.1.0" }',
                ),
                line=line_num,
                column=1,
            )
        table[key] = raw_value[1:-1]
    return table


def _split_inline_parts(text: str) -> List[str]:
    parts: List[str] = []
    current = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            current.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
            current.append(ch)
            continue
        if ch == "," and not in_string:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(ch)
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts
