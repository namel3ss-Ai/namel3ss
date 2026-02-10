from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.slugify import slugify_text


@dataclass(frozen=True)
class PluginCreateResult:
    target: Path
    files: tuple[str, ...]
    dry_run: bool


def scaffold_plugin_package(name: str, root: Path, *, dry_run: bool = False) -> PluginCreateResult:
    plugin_name = _normalize_name(name)
    component_name = _component_name(plugin_name)
    target = (root / plugin_name).resolve()
    files = _render_files(plugin_name=plugin_name, component_name=component_name)
    if target.exists():
        raise Namel3ssError(_existing_dir_message(target))
    if dry_run:
        return PluginCreateResult(target=target, files=tuple(sorted(files.keys())), dry_run=True)
    target.mkdir(parents=True, exist_ok=False)
    for rel_path in sorted(files.keys()):
        file_path = target / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(files[rel_path], encoding="utf-8")
    return PluginCreateResult(target=target, files=tuple(sorted(files.keys())), dry_run=False)


def _normalize_name(value: str) -> str:
    slug = slugify_text(value)
    if slug:
        return slug
    raise Namel3ssError(
        build_guidance_message(
            what="Plugin name is required.",
            why="The create command received an empty plugin name.",
            fix="Pass a non-empty plugin name.",
            example="n3 create plugin chart_panel",
        )
    )


def _component_name(plugin_name: str) -> str:
    parts = [segment for segment in plugin_name.split("_") if segment]
    if not parts:
        return "CustomPanel"
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _render_files(*, plugin_name: str, component_name: str) -> dict[str, str]:
    plugin_manifest = (
        "{\n"
        f'  "name": "{plugin_name}",\n'
        '  "version": "0.1.0",\n'
        '  "module": "renderer.py",\n'
        '  "asset_js": ["assets/runtime.js"],\n'
        '  "asset_css": ["assets/style.css"],\n'
        '  "capabilities": ["ui.plugins"],\n'
        '  "permissions": ["ui"],\n'
        '  "components": [\n'
        "    {\n"
        f'      "name": "{component_name}",\n'
        '      "props": {\n'
        '        "label": {"type": "string", "required": false},\n'
        '        "value": {"type": "string", "required": false}\n'
        "      },\n"
        '      "events": ["onClick"]\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )
    renderer = (
        "def render(props, state):\n"
        "    label = props[\"label\"] if \"label\" in props else \"Plugin component\"\n"
        "    value = props[\"value\"] if \"value\" in props else \"ready\"\n"
        "    return [{\"type\": \"text\", \"text\": label + \": \" + value}]\n"
    )
    runtime_js = (
        "(() => {\n"
        "  if (typeof window === \"undefined\") return;\n"
        "  window.__n3PluginRuntimeLoaded = true;\n"
        "})();\n"
    )
    style_css = (
        ".n3-plugin-sample {\n"
        "  font-weight: 600;\n"
        "}\n"
    )
    translations_en = (
        "{\n"
        '  "schema_version": "1",\n'
        '  "source_locale": "en",\n'
        '  "messages": {\n'
        '    "plugin.title": {"en": "Plugin component"}\n'
        "  }\n"
        "}\n"
    )
    readme = (
        f"# {plugin_name}\n\n"
        "Deterministic Namel3ss plugin scaffold with i18n-ready assets.\n\n"
        "## Capabilities\n"
        "- `ui.plugins`\n"
        "- `sandbox` (resolved via runtime plugin gate)\n\n"
        "## Files\n"
        "- `plugin.json`: plugin manifest\n"
        "- `renderer.py`: sandboxed renderer\n"
        "- `assets/runtime.js`: optional runtime script\n"
        "- `assets/style.css`: optional styles\n"
        "- `translations/en.json`: localization starter catalog\n"
        "- `tests/test_plugin_manifest.py`: manifest validation test\n"
    )
    test_file = (
        "from __future__ import annotations\n\n"
        "import json\n"
        "from pathlib import Path\n\n"
        "from namel3ss.plugins.plugin_manifest import parse_plugin_manifest_contract\n\n\n"
        "def test_plugin_manifest_contract_parses() -> None:\n"
        "    root = Path(__file__).resolve().parents[1]\n"
        "    payload = json.loads((root / \"plugin.json\").read_text(encoding=\"utf-8\"))\n"
        "    contract = parse_plugin_manifest_contract(payload, source_path=root / \"plugin.json\", plugin_root=root)\n"
        f"    assert contract.name == \"{plugin_name}\"\n"
        f"    assert contract.components[0].name == \"{component_name}\"\n"
    )
    return {
        "README.md": readme,
        "plugin.json": plugin_manifest,
        "renderer.py": renderer,
        "assets/runtime.js": runtime_js,
        "assets/style.css": style_css,
        "translations/en.json": translations_en,
        "tests/test_plugin_manifest.py": test_file,
    }


def _existing_dir_message(path: Path) -> str:
    return build_guidance_message(
        what=f"Directory already exists: {path.as_posix()}.",
        why="Scaffolding cannot overwrite an existing plugin directory.",
        fix="Choose a different plugin name or remove the existing folder.",
        example="n3 create plugin chart_panel",
    )


__all__ = ["PluginCreateResult", "scaffold_plugin_package"]
