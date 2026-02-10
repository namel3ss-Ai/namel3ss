from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ui.patterns import build_rag_chat_pattern
from namel3ss.utils.slugify import slugify_text


@dataclass(frozen=True)
class RagAppScaffoldResult:
    target: Path
    files: tuple[str, ...]
    dry_run: bool


def scaffold_rag_chat_app(
    name: str,
    root: Path,
    *,
    dry_run: bool = False,
    include_i18n: bool = False,
    include_plugins: bool = False,
    include_profiling: bool = False,
) -> RagAppScaffoldResult:
    app_name = _normalize_name(name)
    target = (root / app_name).resolve()
    files = _render_files(
        app_name,
        include_i18n=include_i18n,
        include_plugins=include_plugins,
        include_profiling=include_profiling,
    )
    if target.exists():
        raise Namel3ssError(_existing_dir_message(target))
    if dry_run:
        return RagAppScaffoldResult(target=target, files=tuple(sorted(files.keys())), dry_run=True)
    target.mkdir(parents=True, exist_ok=False)
    for rel_path in sorted(files):
        path = target / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[rel_path], encoding="utf-8")
    return RagAppScaffoldResult(target=target, files=tuple(sorted(files.keys())), dry_run=False)


def _normalize_name(value: str) -> str:
    slug = slugify_text(value)
    if slug:
        return slug
    raise Namel3ssError(
        build_guidance_message(
            what="RAG app name is required.",
            why="The create command received an empty app name.",
            fix="Pass a non-empty rag_app name.",
            example="n3 create rag_app support_assistant",
        )
    )


def _render_files(
    app_name: str,
    *,
    include_i18n: bool,
    include_plugins: bool,
    include_profiling: bool,
) -> dict[str, str]:
    pattern_fragment = build_rag_chat_pattern(
        capabilities=("ui.rag_patterns",),
        studio_mode=False,
    )
    manifest_text = canonical_json_dumps(pattern_fragment, pretty=True, drop_run_keys=False)
    capabilities = ["ui.custom_layouts", "ui.rag_patterns"]
    if include_i18n:
        capabilities.append("ui.i18n")
    if include_plugins:
        capabilities.append("ui.plugins")
    capabilities_text = "\n".join(f"  {item}" for item in capabilities)
    app_sections = [
        'spec is "1.0"\n\n',
        "capabilities:\n",
        f"{capabilities_text}\n\n",
        'flow "send_message":\n',
        '  return "ok"\n\n',
        'flow "retry_ingestion":\n',
        '  return "ok"\n\n',
    ]
    if include_plugins:
        app_sections.append('use plugin "sample_plugin"\n\n')
    app_sections.extend(
        [
            f'page "{app_name}":\n',
            f'  title is "{app_name}"\n',
            '  text is "This app was scaffolded with the RAG chat pattern."\n',
            '  text is "Use patterns/rag_chat.json as the deterministic manifest fragment source."\n',
        ]
    )
    app_text = "".join(app_sections)
    readme_text = (
        f"# {app_name}\n\n"
        "Deterministic RAG app scaffold using Phase 3 patterns.\n\n"
        "## Files\n"
        "- `app.ai`: minimal app entrypoint.\n"
        "- `patterns/rag_chat.json`: generated high-level RAG pattern fragment.\n"
        "- `docs/notes.md`: usage notes for pattern state and actions.\n\n"
        "## Next steps\n"
        "1. Wire chat and ingestion flows to your runtime handlers.\n"
        "2. Keep action/state keys stable.\n"
        "3. Use `ui.rag_patterns` for high-level RAG components.\n"
    )
    if include_i18n:
        readme_text += "4. Configure `i18n/config.json` and locale bundles in `i18n/locales`.\n"
    if include_plugins:
        readme_text += "5. Add plugin metadata under `plugins/sample_plugin` and keep capabilities explicit.\n"
    if include_profiling:
        readme_text += "6. Run `python tools/profile_app.py` to collect compile-time profile metrics.\n"
    notes_text = (
        "# Pattern Notes\n\n"
        "State contract:\n"
        "- `chatState.messages`\n"
        "- `chatState.citations`\n"
        "- `chatState.streaming`\n"
        "- `ingestionState.status`\n\n"
        "Action contract:\n"
        "- `component.chat.send`\n"
        "- `component.citation.open`\n"
        "- `component.document.select`\n"
        "- `component.ingestion.retry`\n"
    )
    files = {
        "README.md": readme_text,
        "app.ai": app_text,
        "docs/notes.md": notes_text,
        "patterns/rag_chat.json": manifest_text,
    }
    if include_i18n:
        files["i18n/config.json"] = (
            "{\n"
            '  "locale": "en",\n'
            '  "fallback_locale": "en",\n'
            '  "locales": ["en", "fr", "ar"],\n'
            '  "translations": {\n'
            '    "en": "i18n/locales/en.json",\n'
            '    "fr": "i18n/locales/fr.json",\n'
            '    "ar": "i18n/locales/ar.json"\n'
            "  }\n"
            "}\n"
        )
        files["i18n/locales/en.json"] = (
            "{\n"
            '  "locale": "en",\n'
            '  "fallback_locale": "en",\n'
            '  "messages": {\n'
            '    "manifest.pages.0.title": {"en": "RAG Shell"}\n'
            "  }\n"
            "}\n"
        )
    if include_plugins:
        files["plugins/sample_plugin/plugin.json"] = (
            "{\n"
            '  "name": "sample_plugin",\n'
            '  "version": "0.1.0",\n'
            '  "module": "renderer.py",\n'
            '  "capabilities": ["ui.plugins"],\n'
            '  "permissions": ["ui"],\n'
            '  "components": [\n'
            '    {"name": "SamplePanel", "props": {"label": "string"}, "events": ["onClick"]}\n'
            "  ]\n"
            "}\n"
        )
        files["plugins/sample_plugin/renderer.py"] = (
            "def render(props, state):\n"
            "    return [{\"type\": \"text\", \"text\": props[\"label\"] if \"label\" in props else \"sample\"}]\n"
        )
    if include_profiling:
        files["tools/profile_app.py"] = (
            "from pathlib import Path\n\n"
            "from namel3ss.performance.profiler import profile_app_build\n\n\n"
            "def main() -> int:\n"
            "    app_path = Path(__file__).resolve().parents[1] / \"app.ai\"\n"
            "    profile = profile_app_build(app_path, iterations=3, enabled=True)\n"
            "    print(profile.as_dict())\n"
            "    return 0\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    raise SystemExit(main())\n"
        )
    return files


def _existing_dir_message(path: Path) -> str:
    return build_guidance_message(
        what=f"Directory already exists: {path.as_posix()}.",
        why="Scaffolding cannot overwrite an existing app directory.",
        fix="Choose a different app name or remove the existing folder.",
        example="n3 create rag_app support_assistant",
    )


__all__ = ["RagAppScaffoldResult", "scaffold_rag_chat_app"]
