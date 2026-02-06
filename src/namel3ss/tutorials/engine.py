from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from namel3ss.determinism import canonical_json_dump
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader import load_project
from namel3ss.utils.simple_yaml import parse_yaml


@dataclass(frozen=True)
class TutorialStep:
    instruction: str
    code: str
    expected_output: str


@dataclass(frozen=True)
class TutorialDefinition:
    slug: str
    title: str
    requires: str
    tags: tuple[str, ...]
    steps: tuple[TutorialStep, ...]


PROGRESS_FILE = "tutorial_progress.json"


def list_tutorials() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for path in _library_root().glob("*.yaml"):
        tutorial = load_tutorial(path.stem)
        items.append(
            {
                "slug": tutorial.slug,
                "title": tutorial.title,
                "requires": tutorial.requires,
                "tags": list(tutorial.tags),
                "steps": len(tutorial.steps),
            }
        )
    items.sort(key=lambda item: str(item.get("slug") or ""))
    return items


def load_tutorial(slug: str) -> TutorialDefinition:
    target = _library_root() / f"{slug}.yaml"
    if not target.exists():
        raise Namel3ssError(_missing_tutorial_message(slug))
    payload = parse_yaml(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_tutorial_message(slug, "expected a YAML map"))

    resolved_slug = _require_text(payload.get("slug"), "slug", slug)
    title = _require_text(payload.get("title"), "title", slug)
    requires = _require_text(payload.get("requires"), "requires", slug)
    tags = _parse_tags(payload.get("tags"), slug)
    steps = _parse_steps(payload.get("steps"), slug)
    return TutorialDefinition(slug=resolved_slug, title=title, requires=requires, tags=tags, steps=steps)


def load_tutorial_progress(project_root: Path) -> dict[str, dict[str, object]]:
    path = _progress_path(project_root)
    if not path.exists():
        return {}
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, dict[str, object]] = {}
    for key in sorted(payload.keys()):
        value = payload.get(key)
        if not isinstance(value, dict):
            continue
        normalized[str(key)] = {
            "completed": bool(value.get("completed", False)),
            "step_count": int(value.get("step_count", 0)),
            "last_passed": int(value.get("last_passed", 0)),
        }
    return normalized


def run_tutorial(
    slug: str,
    *,
    project_root: Path,
    answers: list[str] | None = None,
    auto: bool = False,
    input_reader: Callable[[str], str] | None = None,
) -> dict[str, object]:
    tutorial = load_tutorial(slug)
    reader = input_reader or input
    answer_list = list(answers or [])

    results: list[dict[str, object]] = []
    passed_steps = 0
    for index, step in enumerate(tutorial.steps, start=1):
        validation = _validate_step_code(step.code)
        expected = step.expected_output
        if auto:
            response = expected
        elif answer_list:
            response = answer_list.pop(0)
        else:
            prompt = f"Step {index}/{len(tutorial.steps)}: {step.instruction}\nYour answer: "
            response = reader(prompt)
        passed = bool(validation.get("ok")) and (not expected or response.strip() == expected.strip())
        if passed:
            passed_steps += 1
        results.append(
            {
                "step": index,
                "instruction": step.instruction,
                "expected_output": expected,
                "response": response,
                "parse_ok": bool(validation.get("ok")),
                "parse_error": validation.get("error"),
                "passed": passed,
            }
        )

    completed = passed_steps == len(tutorial.steps)
    progress = load_tutorial_progress(project_root)
    progress[tutorial.slug] = {
        "completed": completed,
        "step_count": len(tutorial.steps),
        "last_passed": passed_steps,
    }
    _write_progress(project_root, progress)

    return {
        "ok": True,
        "slug": tutorial.slug,
        "title": tutorial.title,
        "step_count": len(tutorial.steps),
        "passed_steps": passed_steps,
        "completed": completed,
        "results": results,
    }


def _validate_step_code(source: str) -> dict[str, object]:
    normalized = _normalize_source(source)
    try:
        with TemporaryDirectory(prefix="n3-tutorial-") as tmp:
            app_path = Path(tmp) / "app.ai"
            app_path.write_text(normalized, encoding="utf-8")
            _ = load_project(app_path)
        return {"ok": True}
    except Exception as err:
        return {"ok": False, "error": str(err)}


def _write_progress(project_root: Path, payload: dict[str, dict[str, object]]) -> None:
    normalized = {
        key: {
            "completed": bool(value.get("completed", False)),
            "last_passed": int(value.get("last_passed", 0)),
            "step_count": int(value.get("step_count", 0)),
        }
        for key, value in sorted(payload.items(), key=lambda item: item[0])
    }
    canonical_json_dump(_progress_path(project_root), normalized, pretty=True, drop_run_keys=False)


def _progress_path(project_root: Path) -> Path:
    return project_root / ".namel3ss" / PROGRESS_FILE


def _library_root() -> Path:
    return Path(__file__).resolve().parent / "library"


def _normalize_source(source: str) -> str:
    text = source.replace("\\r\\n", "\\n").replace("\\r", "\\n")
    stripped = text.lstrip()
    if not stripped:
        return 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'
    if stripped.startswith("spec "):
        return text if text.endswith("\n") else text + "\n"
    prefix = 'spec is "1.0"\n\n'
    merged = prefix + text
    return merged if merged.endswith("\n") else merged + "\n"


def _parse_steps(raw: object, slug: str) -> tuple[TutorialStep, ...]:
    if not isinstance(raw, list) or not raw:
        raise Namel3ssError(_invalid_tutorial_message(slug, "steps must be a non-empty list"))
    steps: list[TutorialStep] = []
    for item in raw:
        if not isinstance(item, dict):
            raise Namel3ssError(_invalid_tutorial_message(slug, "each step must be a map"))
        instruction = _require_text(item.get("instruction"), "steps.instruction", slug)
        code = _decode_multiline(_require_text(item.get("code"), "steps.code", slug))
        expected = _decode_multiline(_require_text(item.get("expected_output"), "steps.expected_output", slug))
        steps.append(TutorialStep(instruction=instruction, code=code, expected_output=expected))
    return tuple(steps)


def _parse_tags(raw: object, slug: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise Namel3ssError(_invalid_tutorial_message(slug, "tags must be a list"))
    cleaned = [str(item).strip() for item in raw if isinstance(item, str) and str(item).strip()]
    return tuple(sorted(set(cleaned)))


def _decode_multiline(value: str) -> str:
    decoded = value.replace("\\\\n", "\n")
    decoded = decoded.replace('\\"', '"')
    decoded = decoded.replace("\\\\t", "\t")
    return decoded


def _require_text(value: object, field: str, slug: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(_invalid_tutorial_message(slug, f"{field} is required"))
    return value.strip()


def _missing_tutorial_message(slug: str) -> str:
    return build_guidance_message(
        what=f"Tutorial '{slug}' was not found.",
        why="The lesson slug does not match any tutorial file.",
        fix="Run n3 tutorial list and pick a valid slug.",
        example="n3 tutorial list",
    )


def _invalid_tutorial_message(slug: str, details: str) -> str:
    return build_guidance_message(
        what=f"Tutorial '{slug}' is invalid.",
        why=details,
        fix="Fix the tutorial YAML fields and retry.",
        example="slug: basics",
    )


__all__ = [
    "PROGRESS_FILE",
    "TutorialDefinition",
    "TutorialStep",
    "list_tutorials",
    "load_tutorial",
    "load_tutorial_progress",
    "run_tutorial",
]
