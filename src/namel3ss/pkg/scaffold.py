from __future__ import annotations

import hashlib
import json
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def scaffold_package(name: str, root: Path) -> Path:
    package_name = _normalize_name(name)
    target = root / package_name
    if target.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Target directory already exists: {target}",
                why="Package scaffolding will not overwrite existing files.",
                fix="Choose a new name or remove the existing directory.",
                example=f"n3 new pkg {package_name}",
            )
        )
    module_dir = target / "modules" / package_name
    docs_dir = target / "docs"
    tests_dir = target / "tests"
    target.mkdir(parents=True, exist_ok=True)
    module_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    capsule = _capsule_template(package_name)
    (target / "capsule.ai").write_text(capsule, encoding="utf-8")
    (module_dir / "capsule.ai").write_text(capsule, encoding="utf-8")
    (module_dir / "logic.ai").write_text(_logic_template(), encoding="utf-8")
    (target / "app.ai").write_text(_app_template(package_name), encoding="utf-8")
    (tests_dir / f"{package_name}_test.ai").write_text(_test_template(package_name), encoding="utf-8")
    (target / "README.md").write_text(_readme_template(package_name), encoding="utf-8")
    (docs_dir / "README.md").write_text(_docs_template(), encoding="utf-8")
    (target / "LICENSE").write_text("TODO: Choose a license.\n", encoding="utf-8")
    (target / "namel3ss.toml").write_text(_toml_template(package_name), encoding="utf-8")

    metadata = {
        "name": package_name,
        "version": "0.1.0",
        "source": f"github:namel3ss-ai/{package_name}@v0.1.0",
        "license_file": "LICENSE",
        "checksums": "checksums.json",
    }
    (target / "namel3ss.package.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    _write_checksums(target)
    return target


def _normalize_name(name: str) -> str:
    cleaned = name.strip().replace(" ", "-")
    if not cleaned:
        raise Namel3ssError("Package name cannot be empty.")
    return cleaned


def _capsule_template(name: str) -> str:
    return (
        f'capsule "{name}":\n'
        "  exports:\n"
        '    flow "hello"\n'
    )


def _logic_template() -> str:
    return 'flow "hello":\n  return "ok"\n'


def _app_template(name: str) -> str:
    return (
        f'use "{name}" as pkg\n\n'
        'flow "demo":\n  return pkg.hello\n'
    )


def _test_template(name: str) -> str:
    return (
        f'use "{name}" as pkg\n\n'
        'test "hello":\n'
        '  run flow "pkg.hello" with input: {} as result\n'
        '  expect value is "ok"\n'
    )


def _readme_template(name: str) -> str:
    return (
        f"# {name}\n\n"
        "Short description here.\n\n"
        "## Install\n\n"
        f"`n3 pkg add github:namel3ss-ai/{name}@v0.1.0`\n\n"
        "## Usage\n\n"
        "- Exported flows are listed in capsule.ai.\n"
    )


def _docs_template() -> str:
    return "Add docs and design notes here.\n"


def _toml_template(name: str) -> str:
    return (
        "[package]\n"
        f"name = \"{name}\"\n"
        "version = \"0.1.0\"\n"
        "license = \"UNLICENSED\"\n"
        "\n"
    )


def _write_checksums(root: Path) -> None:
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "checksums.json":
            continue
        rel = path.relative_to(root).as_posix()
        files[rel] = f"sha256:{_sha256(path)}"
    payload = {"files": files}
    (root / "checksums.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


__all__ = ["scaffold_package"]
