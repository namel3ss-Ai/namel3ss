from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.specs import parse_source_spec
from namel3ss.pkg.types import DependencySpec, Manifest
from namel3ss.pkg.versions import parse_constraint, parse_semver


MANIFEST_FILENAME = "namel3ss.toml"
METADATA_FILENAME = "namel3ss.package.json"


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
    package_name, package_version, capabilities = _parse_package_block(data.get("package"))
    metadata_payload = _load_metadata_payload(root)
    if metadata_payload is not None:
        package_name = package_name or _optional_text(metadata_payload.get("name"))
        package_version = package_version or _optional_text(metadata_payload.get("version"))
        if not capabilities:
            capabilities = _parse_capabilities(metadata_payload.get("capabilities"))
        metadata_deps = metadata_payload.get("dependencies")
        if isinstance(metadata_deps, dict):
            for dep_name, dep_value in metadata_deps.items():
                parsed_dep = _parse_dependency(dep_name, dep_value)
                existing = parsed.get(dep_name)
                if existing is None:
                    parsed[dep_name] = parsed_dep
                elif existing.source.as_string() != parsed_dep.source.as_string() or existing.constraint_raw != parsed_dep.constraint_raw:
                    raise Namel3ssError(
                        build_guidance_message(
                            what=f"Dependency '{dep_name}' differs between {MANIFEST_FILENAME} and {METADATA_FILENAME}.",
                            why="The same dependency must resolve to one deterministic source and version constraint.",
                            fix="Align dependency source/version values in both manifests.",
                            example=f'{dep_name} = {{ source = "github:owner/repo@v0.1.0", version = "^0.1" }}',
                        )
                    )
    return Manifest(
        dependencies=parsed,
        package_name=package_name,
        package_version=package_version,
        capabilities=capabilities,
        path=path,
    )


def load_manifest_optional(root: Path) -> Manifest:
    path = root / MANIFEST_FILENAME
    if not path.exists():
        metadata_payload = _load_metadata_payload(root)
        if metadata_payload is None:
            return Manifest(dependencies={}, path=path)
        package_name = _optional_text(metadata_payload.get("name"))
        package_version = _optional_text(metadata_payload.get("version"))
        capabilities = _parse_capabilities(metadata_payload.get("capabilities"))
        dependencies: Dict[str, DependencySpec] = {}
        raw_deps = metadata_payload.get("dependencies")
        if isinstance(raw_deps, dict):
            for name, value in raw_deps.items():
                dependencies[str(name)] = _parse_dependency(str(name), value)
        return Manifest(
            dependencies=dependencies,
            package_name=package_name,
            package_version=package_version,
            capabilities=capabilities,
            path=path,
        )
    return load_manifest(root)


def write_manifest(root: Path, manifest: Manifest) -> Path:
    path = root / MANIFEST_FILENAME
    path.write_text(format_manifest(manifest), encoding="utf-8")
    return path


def format_manifest(manifest: Manifest) -> str:
    lines: List[str] = []
    if manifest.package_name or manifest.package_version or manifest.capabilities:
        lines.append("[package]")
        if manifest.package_name:
            lines.append(f'name = "{manifest.package_name}"')
        if manifest.package_version:
            lines.append(f'version = "{manifest.package_version}"')
        if manifest.capabilities:
            caps = ", ".join(f'"{item}"' for item in manifest.capabilities)
            lines.append(f"capabilities = [{caps}]")
        lines.append("")
    lines.append("[dependencies]")
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
    if value.startswith("[") and value.endswith("]"):
        return _parse_string_array(value, line_num, path)
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


def _parse_package_block(value: object) -> tuple[str | None, str | None, tuple[str, ...]]:
    if value is None:
        return None, None, ()
    if not isinstance(value, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="Package section is not a table.",
                why="package metadata must be declared under [package].",
                fix="Use [package] with name/version/capabilities fields.",
                example='[package]\nname = "inventory"\nversion = "0.1.0"',
            )
        )
    name = _optional_text(value.get("name"))
    version = _optional_text(value.get("version"))
    capabilities = _parse_capabilities(value.get("capabilities"))
    return name, version, capabilities


def _parse_capabilities(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    values: list[str] = []
    if isinstance(value, str):
        values = [token.strip() for token in value.split(",") if token.strip()]
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                values.append(item.strip())
    else:
        raise Namel3ssError(
            build_guidance_message(
                what="Package capabilities value is invalid.",
                why="Capabilities must be a string list or comma-separated string.",
                fix='Use capabilities = ["http", "security_compliance"]',
                example='capabilities = ["versioning_quality_mlops"]',
            )
        )
    return tuple(sorted(set(values)))


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def _load_metadata_payload(root: Path) -> dict[str, Any] | None:
    path = root / METADATA_FILENAME
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what=f"{METADATA_FILENAME} is invalid JSON.",
                why=f"Unable to parse metadata file: {err}.",
                fix=f"Fix {METADATA_FILENAME} syntax and retry.",
                example='{"name":"inventory","version":"0.1.0"}',
            )
        ) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(
            build_guidance_message(
                what=f"{METADATA_FILENAME} must be a JSON object.",
                why="Top-level metadata must be key/value pairs.",
                fix="Wrap metadata in a JSON object.",
                example='{"name":"inventory","version":"0.1.0"}',
            )
        )
    return payload


def _parse_string_array(value: str, line_num: int, path: Path) -> list[str]:
    inner = value[1:-1].strip()
    if not inner:
        return []
    parts = _split_inline_parts(inner)
    values: list[str] = []
    for part in parts:
        text = part.strip()
        if not (text.startswith('"') and text.endswith('"')):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Invalid array value in {path.name}.",
                    why="Only arrays of quoted strings are supported.",
                    fix='Use values like ["http", "jobs"].',
                    example='capabilities = ["security_compliance"]',
                ),
                line=line_num,
                column=1,
            )
        values.append(text[1:-1])
    return values
