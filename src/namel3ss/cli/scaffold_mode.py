from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.format import format_source
from namel3ss.lint.engine import lint_source
from namel3ss.pkg.scaffold import scaffold_package
from namel3ss.resources import templates_root
from namel3ss.cli.demo_support import CLEARORDERS_NAME, DEMO_MARKER


@dataclass(frozen=True)
class TemplateSpec:
    name: str
    directory: str
    description: str
    aliases: tuple[str, ...] = ()
    is_demo: bool = False

    def matches(self, candidate: str) -> bool:
        normalized = candidate.lower().replace("_", "-")
        if normalized == self.name:
            return True
        normalized_aliases = {alias.lower().replace("_", "-") for alias in self.aliases}
        normalized_aliases.add(self.directory.lower().replace("_", "-"))
        return normalized in normalized_aliases


TEMPLATES: tuple[TemplateSpec, ...] = (
    TemplateSpec(
        name="demo",
        directory="clear_orders",
        description="ClearOrders demo for explainable answers over structured data.",
        aliases=("clear-orders", "clear_orders"),
        is_demo=True,
    ),
    TemplateSpec(name="starter", directory="starter", description="Small app with one page and one flow."),
    TemplateSpec(name="crud", directory="crud", description="CRUD dashboard with form and table."),
    TemplateSpec(
        name="ai-assistant",
        directory="ai_assistant",
        description="AI assistant over records with memory and tooling.",
        aliases=("ai_assistant",),
    ),
    TemplateSpec(
        name="multi-agent",
        directory="multi_agent",
        description="Planner, critic, and researcher agents sharing one assistant.",
        aliases=("multi_agent",),
    ),
    TemplateSpec(
        name="agent-lab",
        directory="agent_lab",
        description="Agent Lab starter with explainable runs and safe tool defaults.",
        aliases=("agent_lab",),
    ),
    TemplateSpec(
        name="agent-wow",
        directory="agent_wow",
        description="Premium multi-agent demo with governed memory handoffs.",
        aliases=("agent_wow",),
    ),
)


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
    if len(args) > 2:
        raise Namel3ssError("Usage: n3 new template name")
    template_name = args[0]
    template = _resolve_template(template_name)
    project_input = args[1] if len(args) == 2 else template.name
    project_name = _normalize_project_name(project_input)

    template_dir = _templates_root() / template.directory
    if not template_dir.exists():
        raise Namel3ssError(f"Template '{template.name}' is not installed. Missing {template_dir}.")

    target_dir = Path.cwd() / project_name
    if target_dir.exists():
        raise Namel3ssError(f"Directory already exists: {target_dir}")

    demo_settings = _resolve_demo_settings() if template.is_demo else None
    try:
        shutil.copytree(template_dir, target_dir)
        _prepare_readme(target_dir, project_name)
        formatted_source = _prepare_app_file(target_dir, project_name, template, demo_settings)
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
    longest = max(len(t.name) for t in TEMPLATES)
    lines = ["Available templates:"]
    for template in TEMPLATES:
        padded = template.name.ljust(longest)
        lines.append(f"  {padded} - {template.description}")
    return "\n".join(lines)


def _templates_root() -> Path:
    return templates_root()


def _resolve_template(name: str) -> TemplateSpec:
    for template in TEMPLATES:
        if template.matches(name):
            return template
    available = ", ".join(t.name for t in TEMPLATES)
    raise Namel3ssError(f"Unknown template '{name}'. Available templates: {available}")


def _normalize_project_name(name: str) -> str:
    normalized = name.replace("-", "_")
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", normalized).strip("_")
    if not normalized:
        raise Namel3ssError("Project name cannot be empty after normalization")
    return normalized


def _prepare_readme(target_dir: Path, project_name: str) -> None:
    readme_path = target_dir / "README.md"
    if not readme_path.exists():
        return
    _rewrite_with_project_name(readme_path, project_name)


def _prepare_app_file(
    target_dir: Path,
    project_name: str,
    template: TemplateSpec,
    demo_settings: DemoSettings | None,
) -> str:
    app_path = target_dir / "app.ai"
    if not app_path.exists():
        raise Namel3ssError(f"Template is missing app.ai at {app_path}")
    raw = _rewrite_with_project_name(app_path, project_name)
    if template.name == "demo" and demo_settings:
        raw = _apply_demo_tokens(raw, demo_settings)
    formatted = format_source(raw)
    app_mode = app_path.stat().st_mode
    app_path.write_text(formatted, encoding="utf-8")
    app_path.chmod(app_mode)
    return formatted


def _rewrite_with_project_name(path: Path, project_name: str) -> str:
    original_mode = path.stat().st_mode
    contents = path.read_text(encoding="utf-8")
    updated = contents.replace("{{PROJECT_NAME}}", project_name)
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
        "You are a concise analytics assistant. Answer in 1-3 bullet points. "
        "If the dataset does not contain enough information, say what is missing."
    )
    return DemoSettings(provider=provider, model=model, system_prompt=system_prompt)


def _apply_demo_tokens(contents: str, settings: DemoSettings) -> str:
    replaced = contents
    replaced = replaced.replace("DEMO_PROVIDER", settings.provider)
    replaced = replaced.replace("DEMO_MODEL", settings.model)
    replaced = replaced.replace("DEMO_SYSTEM_PROMPT", settings.system_prompt)
    if "DEMO_PROVIDER" not in contents:
        replaced = replaced.replace('provider is "mock"', f'provider is "{settings.provider}"', 1)
    if "DEMO_MODEL" not in contents:
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
        "# Optional",
        "N3_DEMO_MODEL=gpt-4o-mini",
        "",
    ]
    env_path.write_text("\n".join(lines), encoding="utf-8")


def _ensure_demo_marker(target_dir: Path) -> None:
    marker_path = target_dir / DEMO_MARKER
    if marker_path.exists():
        return
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"name": CLEARORDERS_NAME}
    marker_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _print_success_message(template: TemplateSpec, project_name: str, target_dir: Path) -> None:
    print(f"Created project at {target_dir}")
    if template.name == "demo":
        print(f"Run: cd {project_name} && n3 run")
        return
    print("Next step")
    print(f"  cd {project_name} and run n3 app.ai")
