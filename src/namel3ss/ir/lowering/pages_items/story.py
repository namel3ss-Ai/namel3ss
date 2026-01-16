from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.icons.registry import closest_icon, validate_icon_name, icon_names
from namel3ss.media import validate_media_role
from namel3ss.ir.model.pages import StoryItem, StoryStep
from namel3ss.ui.settings import STORY_TONES, closest_value


def lower_story_item(
    item: ast.StoryItem,
    *,
    attach_origin,
) -> StoryItem:
    lowered_steps: list[StoryStep] = []
    seen_titles: set[str] = set()
    for step in item.steps:
        title = step.title
        if title in seen_titles:
            raise Namel3ssError(
                f"Story '{item.title}' step '{title}' is declared more than once",
                line=step.line,
                column=step.column,
            )
        seen_titles.add(title)
        tone = _validate_tone(step.tone, step.line, step.column)
        icon = _validate_icon(step.icon, step.line, step.column)
        text_value = _normalize_optional(step.text)
        image_value = _normalize_optional(step.image)
        image_role = validate_media_role(step.image_role, line=step.line, column=step.column)
        requires = _normalize_optional(step.requires)
        next_step = _normalize_optional(step.next)
        if step.text is not None and text_value is None:
            raise Namel3ssError("Story text cannot be empty", line=step.line, column=step.column)
        if step.image is not None and image_value is None:
            raise Namel3ssError("Story image cannot be empty", line=step.line, column=step.column)
        if step.requires is not None and requires is None:
            raise Namel3ssError("Story requires cannot be empty", line=step.line, column=step.column)
        if step.next is not None and next_step is None:
            raise Namel3ssError("Story next target cannot be empty", line=step.line, column=step.column)
        lowered_steps.append(
            StoryStep(
                title=title,
                text=text_value,
                icon=icon,
                image=image_value,
                image_role=image_role,
                tone=tone,
                requires=requires,
                next=next_step,
                line=step.line,
                column=step.column,
            )
        )
    _validate_story_next_targets(item.title, lowered_steps)
    _validate_story_cycles(item.title, lowered_steps)
    return attach_origin(StoryItem(title=item.title, steps=lowered_steps, line=item.line, column=item.column), item)


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _validate_tone(value: str | None, line: int | None, column: int | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise Namel3ssError("Story tone cannot be empty", line=line, column=column)
    if normalized in STORY_TONES:
        return normalized
    suggestion = closest_value(normalized, STORY_TONES)
    fix = f'Did you mean "{suggestion}"?' if suggestion else f"Use one of: {', '.join(STORY_TONES)}."
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown story tone '{normalized}'.",
            why=f"Allowed tones: {', '.join(STORY_TONES)}.",
            fix=fix,
            example='story "Onboarding"\n  step "Start":\n    tone is "informative"',
        ),
        line=line,
        column=column,
    )


def _validate_icon(value: str | None, line: int | None, column: int | None) -> str | None:
    if value is None:
        return None
    try:
        return validate_icon_name(value, line=line, column=column)
    except Namel3ssError as err:
        if not err.details:
            err.details = {"error_id": "icon.invalid", "keyword": value}
        suggestion = closest_icon(value) or (icon_names()[0] if icon_names() else None)
        fix = f'Did you mean "{suggestion}"?' if suggestion else "Use a built-in icon from the registry."
        err.message = build_guidance_message(
            what=f"Unknown story icon '{value}'.",
            why="Icons must come from the built-in registry.",
            fix=fix + " Run `n3 icons` to list options.",
            example='story "Checklist"\n  step "Review":\n    icon is add',
        )
        raise


def _validate_story_next_targets(story_title: str, steps: list[StoryStep]) -> None:
    titles = [step.title for step in steps]
    for step in steps:
        if step.next and step.next not in titles:
            suggestion = closest_value(step.next, titles)
            fix = f'Did you mean "{suggestion}"?' if suggestion else "Use an existing step title."
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Story '{story_title}' step '{step.title}' references unknown next step '{step.next}'.",
                    why="Next must point to another step in the same story.",
                    fix=fix,
                    example='story "Onboarding"\n  step "Start":\n    next is "Finish"',
                ),
                line=step.line,
                column=step.column,
            )


def _validate_story_cycles(story_title: str, steps: list[StoryStep]) -> None:
    if len(steps) < 2:
        return
    targets: dict[str, str] = {}
    for idx, step in enumerate(steps):
        target = step.next or (steps[idx + 1].title if idx + 1 < len(steps) else None)
        if target:
            targets[step.title] = target
    visited: set[str] = set()
    active: set[str] = set()
    step_map = {step.title: step for step in steps}

    def _dfs(title: str, path: list[str]) -> None:
        visited.add(title)
        active.add(title)
        target = targets.get(title)
        if target is None:
            active.remove(title)
            return
        if target in active:
            cycle_start = path.index(target) if target in path else 0
            cycle_path = path[cycle_start:] + [target]
            message = build_guidance_message(
                what=f"Story '{story_title}' has a next cycle: " + " -> ".join(cycle_path) + ".",
                why="Next defines progression order and cannot loop forever.",
                fix="Remove or change a next link to break the cycle.",
                example='story "Intro"\n  step "A":\n    next is "B"\n  step "B":\n    next is "Done"',
            )
            offending = step_map.get(title)
            raise Namel3ssError(message, line=getattr(offending, "line", None), column=getattr(offending, "column", None))
        if target not in visited:
            _dfs(target, path + [target])
        active.remove(title)

    for step in steps:
        if step.title not in visited:
            _dfs(step.title, [step.title])


__all__ = ["lower_story_item"]
