from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.format import format_source
from namel3ss.lint.engine import lint_source


@dataclass(frozen=True)
class TemplateSpec:
    name: str
    directory: str
    description: str
    aliases: tuple[str, ...] = ()

    def matches(self, candidate: str) -> bool:
        normalized = candidate.lower().replace("_", "-")
        if normalized == self.name:
            return True
        normalized_aliases = {alias.lower().replace("_", "-") for alias in self.aliases}
        normalized_aliases.add(self.directory.lower().replace("_", "-"))
        return normalized in normalized_aliases


TEMPLATES: tuple[TemplateSpec, ...] = (
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
)


def run_new(args: list[str]) -> int:
    if not args:
        print(render_templates_list())
        return 0
    if len(args) > 2:
        raise Namel3ssError("Usage: n3 new <template> [project_name]")
    template_name = args[0]
    template = _resolve_template(template_name)
    project_input = args[1] if len(args) == 2 else template.name
    project_name = _normalize_project_name(project_input)

    template_dir = _templates_root() / template.directory
    if not template_dir.exists():
        raise Namel3ssError(f"Template '{template.name}' is not installed (missing {template_dir}).")

    target_dir = Path.cwd() / project_name
    if target_dir.exists():
        raise Namel3ssError(f"Directory already exists: {target_dir}")

    try:
        shutil.copytree(template_dir, target_dir)
        _prepare_readme(target_dir, project_name)
        formatted_source = _prepare_app_file(target_dir, project_name)
    except Exception:
        shutil.rmtree(target_dir, ignore_errors=True)
        raise

    findings = lint_source(formatted_source)
    if findings:
        print("Lint findings:")
        for finding in findings:
            location = f"[line {finding.line}, col {finding.column}] " if finding.line else ""
            print(f"  - {location}{finding.code}: {finding.message}")

    _print_success_message(project_name, target_dir)
    return 0


def render_templates_list() -> str:
    longest = max(len(t.name) for t in TEMPLATES)
    lines = ["Available templates:"]
    for template in TEMPLATES:
        padded = template.name.ljust(longest)
        lines.append(f"  {padded} - {template.description}")
    return "\n".join(lines)


def _templates_root() -> Path:
    return Path(__file__).resolve().parent.parent / "templates"


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
        raise Namel3ssError(f"Template is missing README.md at {readme_path}")
    _rewrite_with_project_name(readme_path, project_name)


def _prepare_app_file(target_dir: Path, project_name: str) -> str:
    app_path = target_dir / "app.ai"
    if not app_path.exists():
        raise Namel3ssError(f"Template is missing app.ai at {app_path}")
    raw = _rewrite_with_project_name(app_path, project_name)
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


def _print_success_message(project_name: str, target_dir: Path) -> None:
    print(f"Created project at {target_dir}")
    print("Next steps:")
    print(f"  cd {project_name}")
    print("  n3 app.ai studio")
    print("  n3 app.ai actions")
