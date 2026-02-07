from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.slugify import slugify_text


@dataclass(frozen=True)
class UIPluginScaffoldResult:
    target: Path
    files: tuple[str, ...]
    dry_run: bool


def scaffold_ui_plugin(name: str, root: Path, *, dry_run: bool = False) -> UIPluginScaffoldResult:
    plugin_name = _normalize_name(name)
    component_name = _component_name(plugin_name)
    target = (root / plugin_name).resolve()
    files = _render_files(plugin_name=plugin_name, component_name=component_name)
    if target.exists():
        raise Namel3ssError(_existing_dir_message(target))
    if dry_run:
        return UIPluginScaffoldResult(target=target, files=tuple(sorted(files.keys())), dry_run=True)
    target.mkdir(parents=True, exist_ok=False)
    for rel_path in sorted(files.keys()):
        file_path = target / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(files[rel_path], encoding="utf-8")
    return UIPluginScaffoldResult(target=target, files=tuple(sorted(files.keys())), dry_run=False)


def _normalize_name(value: str) -> str:
    slug = slugify_text(value)
    if slug:
        return slug
    raise Namel3ssError(
        build_guidance_message(
            what="Plugin name is required.",
            why="The create command received an empty name.",
            fix="Pass a non-empty plugin name.",
            example="n3 create plugin maps",
        )
    )


def _component_name(plugin_name: str) -> str:
    parts = [segment for segment in plugin_name.split("_") if segment]
    if not parts:
        return "CustomComponent"
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _render_files(*, plugin_name: str, component_name: str) -> dict[str, str]:
    plugin_manifest = (
        "{\n"
        f'  "name": "{plugin_name}",\n'
        f'  "version": "0.1.0",\n'
        '  "module": "renderer.py",\n'
        "  \"components\": [\n"
        "    {\n"
        f'      "name": "{component_name}",\n'
        "      \"props\": {\n"
        '        "label": {\n'
        '          "type": "string",\n'
        '          "required": false\n'
        "        }\n"
        "      },\n"
        '      "events": ["onClick"]\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )
    renderer = (
        "def render(props, state):\n"
        "    return [\n"
        "        {\n"
        '            "type": "text",\n'
        '            "text": props[\"label\"] if \"label\" in props else \"Hello from custom UI plugin\",\n'
        "        }\n"
        "    ]\n"
    )
    readme = (
        f"# {plugin_name}\n\n"
        "UI plugin scaffold for Namel3ss custom components.\n\n"
        "## Files\n"
        "- `plugin.json`: plug-in manifest schema and component contracts.\n"
        "- `renderer.py`: sandboxed deterministic renderer (`render(props, state)`).\n"
        "- `tests/test_plugin_manifest.py`: schema parse smoke test.\n\n"
        "## Use in app\n"
        "```ai\n"
        "capabilities:\n"
        "  custom_ui\n"
        "  sandbox\n\n"
        f"use plugin \"{plugin_name}\"\n"
        "```\n"
    )
    test_file = (
        "from __future__ import annotations\n\n"
        "import json\n"
        "from pathlib import Path\n\n"
        "from namel3ss.ui.plugins.schema import parse_plugin_manifest\n\n\n"
        "def test_plugin_manifest_parses() -> None:\n"
        "    root = Path(__file__).resolve().parents[1]\n"
        "    payload = json.loads((root / \"plugin.json\").read_text(encoding=\"utf-8\"))\n"
        "    schema = parse_plugin_manifest(payload, source_path=root / \"plugin.json\", plugin_root=root)\n"
        f"    assert schema.name == \"{plugin_name}\"\n"
        f"    assert schema.components[0].name == \"{component_name}\"\n"
    )
    return {
        "README.md": readme,
        "plugin.json": plugin_manifest,
        "renderer.py": renderer,
        "tests/test_plugin_manifest.py": test_file,
    }


def _existing_dir_message(path: Path) -> str:
    return build_guidance_message(
        what=f"Directory already exists: {path.as_posix()}.",
        why="Scaffolding cannot overwrite an existing plugin directory.",
        fix="Choose a different name or remove the existing folder.",
        example="n3 create plugin charts",
    )


__all__ = ["UIPluginScaffoldResult", "scaffold_ui_plugin"]
