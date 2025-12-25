from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import (
    PACK_BINDINGS,
    PACK_CAPABILITIES,
    PACK_INTENT,
    PACK_MANIFEST,
    PACK_SIGNATURE,
)
from namel3ss.utils.slugify import slugify_tool_name


@dataclass(frozen=True)
class PackInitResult:
    pack_id: str
    path: Path
    files: list[str]
    no_code: bool


def init_pack(pack_id: str, *, target_dir: Path, no_code: bool) -> PackInitResult:
    if not pack_id.strip():
        raise Namel3ssError(_invalid_pack_id_message())
    root = target_dir / pack_id
    if root.exists():
        raise Namel3ssError(_pack_exists_message(root))
    root.mkdir(parents=True, exist_ok=False)
    files: list[str] = []
    tool_name = "echo service" if no_code else "say hello"
    tool_slug = slugify_tool_name(tool_name)
    pack_name = _pack_title(pack_id)
    if no_code:
        _write_text(root / PACK_MANIFEST, _manifest_no_code(pack_id, pack_name, tool_name))
        _write_text(root / PACK_BINDINGS, _bindings_no_code(tool_name))
        _write_text(root / PACK_CAPABILITIES, _capabilities_no_code(tool_name))
        files.extend([PACK_MANIFEST, PACK_BINDINGS, PACK_CAPABILITIES])
    else:
        _write_text(root / PACK_MANIFEST, _manifest_python(pack_id, pack_name, tool_name, tool_slug))
        _write_text(root / "tools" / "__init__.py", "")
        _write_text(root / "tools" / f"{tool_slug}.py", _tool_stub(tool_slug))
        files.extend([PACK_MANIFEST, f"tools/{tool_slug}.py", "tools/__init__.py"])
    _write_text(root / "README.md", _readme(pack_name, tool_name))
    _write_text(root / PACK_INTENT, _intent_template(tool_name))
    _write_text(root / PACK_SIGNATURE, "sha256:TODO\n")
    files.extend(["README.md", PACK_INTENT, PACK_SIGNATURE])
    return PackInitResult(pack_id=pack_id, path=root, files=files, no_code=no_code)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _manifest_no_code(pack_id: str, pack_name: str, tool_name: str) -> str:
    return (
        f'id: "{pack_id}"\n'
        f'name: "{pack_name}"\n'
        'version: "0.1.0"\n'
        'description: "Describe what this pack does."\n'
        'author: "You"\n'
        'license: "MIT"\n'
        "tools:\n"
        f'  - "{tool_name}"\n'
        "runners:\n"
        '  default: "service"\n'
        'service_url: "http://127.0.0.1:8787/tools"\n'
    )


def _manifest_python(pack_id: str, pack_name: str, tool_name: str, tool_slug: str) -> str:
    return (
        f'id: "{pack_id}"\n'
        f'name: "{pack_name}"\n'
        'version: "0.1.0"\n'
        'description: "Describe what this pack does."\n'
        'author: "You"\n'
        'license: "MIT"\n'
        "tools:\n"
        f'  - "{tool_name}"\n'
        "entrypoints:\n"
        f'  "{tool_name}":\n'
        '    kind: "python"\n'
        f'    entry: "tools.{tool_slug}:run"\n'
        '    purity: "pure"\n'
    )


def _bindings_no_code(tool_name: str) -> str:
    return (
        "tools:\n"
        f'  "{tool_name}":\n'
        '    kind: "python"\n'
        '    entry: "service.echo:run"\n'
        '    runner: "service"\n'
        '    url: "http://127.0.0.1:8787/tools"\n'
        '    purity: "impure"\n'
    )


def _capabilities_no_code(tool_name: str) -> str:
    return (
        "capabilities:\n"
        f'  "{tool_name}":\n'
        '    filesystem: "none"\n'
        '    network: "outbound"\n'
        '    env: "none"\n'
        '    subprocess: "none"\n'
        "    secrets: []\n"
    )


def _tool_stub(tool_slug: str) -> str:
    return (
        "def run(payload):\n"
        "    name = payload.get(\"name\", \"there\")\n"
        "    return {\"message\": f\"Hello {name}\", \"ok\": True}\n"
    )


def _intent_template(tool_name: str) -> str:
    return (
        "# Pack Intent\n"
        "## What this pack does\n"
        "Describe the outcome this pack delivers.\n\n"
        "## Tools provided (English)\n"
        f'- "{tool_name}"\n\n'
        "## Inputs/outputs summary\n"
        "Summarize tool inputs and outputs.\n\n"
        "## Capabilities & risk\n"
        "Call out filesystem/network/env/secrets/subprocess usage.\n\n"
        "## Failure modes\n"
        "List expected failure cases and error guidance.\n\n"
        "## Runner requirements\n"
        "Note local/service/container expectations.\n"
    )


def _readme(pack_name: str, tool_name: str) -> str:
    return (
        f"# {pack_name}\n\n"
        "## Tools\n"
        f'- "{tool_name}"\n\n'
        "## Usage\n"
        "Declare the tool in your app and bind it via the pack.\n"
    )


def _pack_title(pack_id: str) -> str:
    parts = [part for part in pack_id.replace("-", ".").split(".") if part]
    return " ".join(part[:1].upper() + part[1:] for part in parts) or pack_id


def _invalid_pack_id_message() -> str:
    return build_guidance_message(
        what="Pack id is missing.",
        why="You must provide a pack id.",
        fix="Pass a pack id like team.pack.",
        example="n3 packs init team.pack",
    )


def _pack_exists_message(path: Path) -> str:
    return build_guidance_message(
        what="Pack directory already exists.",
        why=f"{path.as_posix()} already exists.",
        fix="Choose a new pack id or remove the directory.",
        example="n3 packs init team.pack",
    )


__all__ = ["PackInitResult", "init_pack"]
