from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.format import format_source
from namel3ss.lint.engine import lint_source
from namel3ss.pkg.scaffold import scaffold_package
from namel3ss.resources import templates_root, examples_root
from namel3ss.cli.demo_support import DEMO_MARKER, DEMO_NAME


@dataclass(frozen=True)
class ScaffoldSpec:
    kind: str
    name: str
    directory: str
    description: str
    version: str
    aliases: tuple[str, ...] = ()
    is_demo: bool = False

    def matches(self, candidate: str) -> bool:
        normalized = candidate.lower().replace("_", "-")
        if normalized == self.name:
            return True
        normalized_aliases = {alias.lower().replace("_", "-") for alias in self.aliases}
        normalized_aliases.add(self.directory.lower().replace("_", "-"))
        return normalized in normalized_aliases


_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

TEMPLATES: tuple[ScaffoldSpec, ...] = (
    ScaffoldSpec(
        kind="template",
        name="operations_dashboard",
        directory="operations_dashboard",
        description="Incident-focused ops workspace with a calm dashboard layout.",
        version="0.1.0",
    ),
    ScaffoldSpec(
        kind="template",
        name="onboarding",
        directory="onboarding",
        description="Structured onboarding checklist with guided milestones.",
        version="0.1.0",
    ),
    ScaffoldSpec(
        kind="template",
        name="support_inbox",
        directory="support_inbox",
        description="Support intake and reply flow with an inbox view.",
        version="0.1.0",
    ),
)

EXAMPLES: tuple[ScaffoldSpec, ...] = (
    ScaffoldSpec(
        kind="example",
        name="hello_flow",
        directory="hello_flow",
        description="single-flow example that creates one record and renders it.",
        version="0.1.0",
    ),
)


def _validate_scaffold_specs(specs: tuple[ScaffoldSpec, ...], *, label: str) -> None:
    seen_names: set[str] = set()
    seen_dirs: set[str] = set()
    for spec in specs:
        if spec.name in seen_names:
            raise Namel3ssError(f"Duplicate {label} name '{spec.name}' in scaffold catalog.")
        if spec.directory in seen_dirs:
            raise Namel3ssError(f"Duplicate {label} directory '{spec.directory}' in scaffold catalog.")
        if not _VERSION_RE.match(spec.version):
            raise Namel3ssError(f"{label} '{spec.name}' has invalid version '{spec.version}'.")
        seen_names.add(spec.name)
        seen_dirs.add(spec.directory)


def _validate_catalog() -> None:
    _validate_scaffold_specs(TEMPLATES, label="template")
    _validate_scaffold_specs(EXAMPLES, label="example")
    template_names = {spec.name for spec in TEMPLATES}
    example_names = {spec.name for spec in EXAMPLES}
    collisions = sorted(template_names.intersection(example_names))
    if collisions:
        raise Namel3ssError(f"Template/example name collision: {', '.join(collisions)}")


@dataclass(frozen=True)
class DemoSettings:
    provider: str
    model: str
    system_prompt: str


def run_new(args: list[str]) -> int:
    if not args:
        print(render_templates_list())
        return 0
    if args[0] in {"pkg", "package"}:
        if len(args) < 2:
            raise Namel3ssError("Usage: n3 new pkg name")
        target = scaffold_package(args[1], Path.cwd())
        print(f"Created package at {target}")
        print("Next steps:")
        print(f"  cd {target.name}")
        print("  n3 pkg validate .")
        print("  n3 test")
        return 0
    scaffold_specs = TEMPLATES
    if args[0] in {"example", "examples"}:
        if len(args) < 2:
            raise Namel3ssError("Usage: n3 new example name")
        scaffold_specs = EXAMPLES
        args = args[1:]
    if len(args) > 2:
        usage_kind = "example" if scaffold_specs is EXAMPLES else "template"
        raise Namel3ssError(f"Usage: n3 new {usage_kind} name")
    template_name = args[0]
    template = _resolve_scaffold(template_name, scaffold_specs)
    project_input = args[1] if len(args) == 2 else template.name
    project_name = _normalize_project_name(project_input)

    template_dir = _scaffold_root(template) / template.directory
    if not template_dir.exists():
        raise Namel3ssError(
            f"{template.kind.title()} '{template.name}' is not installed. Missing {template_dir}."
        )

    target_dir = Path.cwd() / project_name
    if target_dir.exists():
        raise Namel3ssError(f"Directory already exists: {target_dir}")

    demo_settings = _resolve_demo_settings() if template.is_demo else None
    try:
        _copy_scaffold_tree(template_dir, target_dir)
        tokens = _build_tokens(project_name, template)
        _prepare_readme(target_dir, tokens)
        formatted_source = _prepare_app_file(target_dir, tokens, template, demo_settings)
        if demo_settings and demo_settings.provider == "openai":
            _write_demo_env_example(target_dir)
        if template.is_demo:
            _ensure_demo_marker(target_dir)
    except Exception:
        shutil.rmtree(target_dir, ignore_errors=True)
        raise

    findings = lint_source(formatted_source)
    if findings:
        print("Lint findings:")
        for finding in findings:
            location = ""
            if finding.line:
                location = f"line {finding.line}"
                if finding.column:
                    location += f" col {finding.column}"
                location = f"{location} "
            print(f"  - {location}{finding.code}: {finding.message}")

    _print_success_message(template, project_name, target_dir)
    return 0


def render_templates_list() -> str:
    longest = max(len(_display_name(t)) for t in TEMPLATES)
    lines = ["Available templates:"]
    for template in TEMPLATES:
        padded = _display_name(template).ljust(longest)
        lines.append(f"  {padded} - {template.description}")
    if EXAMPLES:
        longest_example = max(len(_display_name(e)) for e in EXAMPLES)
        lines.append("")
        lines.append("Examples (read-only):")
        for example in EXAMPLES:
            padded = _display_name(example).ljust(longest_example)
            lines.append(f"  {padded} - {example.description}")
        lines.append("  Scaffold: n3 new example <name>")
    return "\n".join(lines)


def _display_name(spec: ScaffoldSpec) -> str:
    return spec.name.replace("-", " ").replace("_", " ").title()


def _templates_root() -> Path:
    return templates_root()


def _examples_root() -> Path:
    return examples_root()


def _scaffold_root(spec: ScaffoldSpec) -> Path:
    return _templates_root() if spec.kind == "template" else _examples_root()


def _resolve_scaffold(name: str, specs: tuple[ScaffoldSpec, ...]) -> ScaffoldSpec:
    for spec in specs:
        if spec.matches(name):
            return spec
    available = ", ".join(spec.name for spec in specs)
    kind = specs[0].kind if specs else "template"
    raise Namel3ssError(f"Unknown {kind} '{name}'. Available {kind}s: {available}")


def _normalize_project_name(name: str) -> str:
    normalized = name.replace("-", "_")
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", normalized).strip("_")
    if not normalized:
        raise Namel3ssError("Project name cannot be empty after normalization")
    return normalized


def _prepare_readme(target_dir: Path, tokens: dict[str, str]) -> None:
    readme_path = target_dir / "README.md"
    if not readme_path.exists():
        return
    _rewrite_with_tokens(readme_path, tokens)


def _copy_scaffold_tree(source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=False)
    for root, dirs, files in os.walk(source_dir):
        dirs.sort()
        files.sort()
        root_path = Path(root)
        rel_root = root_path.relative_to(source_dir)
        dest_root = target_dir / rel_root
        dest_root.mkdir(parents=True, exist_ok=True)
        for filename in files:
            src_path = root_path / filename
            dest_path = dest_root / filename
            shutil.copy2(src_path, dest_path)


def _prepare_app_file(
    target_dir: Path,
    tokens: dict[str, str],
    template: ScaffoldSpec,
    demo_settings: DemoSettings | None,
) -> str:
    app_path = target_dir / "app.ai"
    if not app_path.exists():
        raise Namel3ssError(f"Template is missing app.ai at {app_path}")
    raw = _rewrite_with_tokens(app_path, tokens)
    if template.name == "demo" and demo_settings:
        raw = _apply_demo_tokens(raw, demo_settings)
    formatted = format_source(raw)
    app_mode = app_path.stat().st_mode
    app_path.write_text(formatted, encoding="utf-8")
    app_path.chmod(app_mode)
    return formatted


def _build_tokens(project_name: str, template: ScaffoldSpec) -> dict[str, str]:
    return {
        "PROJECT_NAME": project_name,
        "TEMPLATE_NAME": template.name,
        "TEMPLATE_VERSION": template.version,
    }


def _rewrite_with_tokens(path: Path, tokens: dict[str, str]) -> str:
    original_mode = path.stat().st_mode
    contents = path.read_text(encoding="utf-8")
    updated = contents
    for key, value in tokens.items():
        updated = updated.replace(f"{{{{{key}}}}}", value)
    path.write_text(updated, encoding="utf-8")
    path.chmod(original_mode)
    return updated


def _resolve_demo_settings() -> DemoSettings:
    provider_env = os.getenv("N3_DEMO_PROVIDER", "").strip().lower()
    provider = "openai" if provider_env == "openai" else "mock"
    model_env = os.getenv("N3_DEMO_MODEL", "").strip()
    if model_env:
        model = model_env
    elif provider == "openai":
        model = "gpt-4o-mini"
    else:
        model = "mock-model"
    system_prompt = (
        "you are a concise assistant. answer in 1-3 short bullets. "
        "if the prompt is missing details, say what is missing."
    )
    return DemoSettings(provider=provider, model=model, system_prompt=system_prompt)


def _apply_demo_tokens(contents: str, settings: DemoSettings) -> str:
    replaced = contents
    replaced = replaced.replace("DEMO_PROVIDER", settings.provider)
    replaced = replaced.replace("DEMO_MODEL", settings.model)
    replaced = replaced.replace("DEMO_SYSTEM_PROMPT", settings.system_prompt)
    replaced = replaced.replace('provider is "mock"', f'provider is "{settings.provider}"', 1)
    replaced = replaced.replace('model is "mock-model"', f'model is "{settings.model}"', 1)
    return replaced


def _write_demo_env_example(target_dir: Path) -> None:
    env_path = target_dir / ".env.example"
    if env_path.exists():
        return
    lines = [
        "# OpenAI (choose one)",
        "OPENAI_API_KEY=",
        "NAMEL3SS_OPENAI_API_KEY=",
        "",
        "# Demo overrides (optional)",
        "N3_DEMO_PROVIDER=",
        "N3_DEMO_MODEL=",
        "",
    ]
    env_path.write_text("\n".join(lines), encoding="utf-8")


def _ensure_demo_marker(target_dir: Path) -> None:
    marker_path = target_dir / DEMO_MARKER
    if marker_path.exists():
        return
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"name": DEMO_NAME}
    marker_path.write_text(canonical_json_dumps(payload, pretty=True), encoding="utf-8")


def _print_success_message(template: ScaffoldSpec, project_name: str, target_dir: Path) -> None:
    print(f"Created project at {target_dir}")
    if template.name == "demo":
        print(f"Run: cd {project_name} && n3 run")
        return
    print("Next step")
    print(f"  cd {project_name} and run n3 app.ai")


_validate_catalog()
