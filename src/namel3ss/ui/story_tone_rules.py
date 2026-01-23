from __future__ import annotations

from dataclasses import dataclass

CANONICAL_TONE_ICONS: dict[str, tuple[str, ...]] = {
    "informative": ("info",),
    "success": ("check",),
    "caution": ("warning",),
    "critical": ("error",),
    "neutral": (),
}

NON_NEUTRAL_TONES = ("informative", "success", "caution", "critical")
MIN_STEPS_FOR_TONE_OVERUSE = 3


@dataclass(frozen=True)
class StoryToneLocation:
    page: str
    page_slug: str
    path: str | None
    line: int | None
    column: int | None

    def sort_key(self) -> tuple[str, int, int]:
        return (
            self.path or "",
            self.line or 0,
            self.column or 0,
        )


@dataclass(frozen=True)
class StoryToneFinding:
    code: str
    message: str
    fix: str
    location: StoryToneLocation

    def sort_key(self) -> tuple[str, str, int, int, str]:
        path = self.location.path or ""
        return (
            self.code,
            path,
            self.location.line or 0,
            self.location.column or 0,
            self.message,
        )


def collect_story_tone_findings(pages: list[dict]) -> list[StoryToneFinding]:
    findings: list[StoryToneFinding] = []
    for page in pages:
        page_name = str(page.get("name") or page.get("slug") or "page")
        page_slug = str(page.get("slug") or page_name)
        elements = page.get("elements") or []
        _walk_story_elements(page_name, page_slug, elements, findings)
    return findings


def _walk_story_elements(
    page_name: str,
    page_slug: str,
    elements: list[dict],
    findings: list[StoryToneFinding],
) -> None:
    for element in elements:
        if not isinstance(element, dict):
            continue
        if element.get("type") == "story":
            findings.extend(_story_tone_findings_for_story(page_name, page_slug, element))
        nested = element.get("children")
        if isinstance(nested, list):
            _walk_story_elements(page_name, page_slug, nested, findings)


def _story_tone_findings_for_story(
    page_name: str,
    page_slug: str,
    element: dict,
) -> list[StoryToneFinding]:
    steps = element.get("steps")
    if not isinstance(steps, list):
        return []
    story_title = _normalize_label(element.get("title")) or "Story"
    story_path = element.get("element_id") or element.get("id")
    line = element.get("line")
    column = element.get("column")
    story_location = StoryToneLocation(
        page=page_name,
        page_slug=page_slug,
        path=story_path,
        line=line,
        column=column,
    )
    findings: list[StoryToneFinding] = []
    non_neutral_count = 0
    step_count = 0

    for step in steps:
        if not isinstance(step, dict):
            continue
        step_count += 1
        tone = _normalize_label(step.get("tone"))
        icon = _normalize_label(step.get("icon"))
        step_title = _normalize_label(step.get("title")) or "step"
        step_path = step.get("id") or story_path
        step_location = StoryToneLocation(
            page=page_name,
            page_slug=page_slug,
            path=step_path,
            line=line,
            column=column,
        )
        if tone in NON_NEUTRAL_TONES:
            non_neutral_count += 1
            if not icon:
                findings.append(
                    rule_tone_missing_icon(
                        story_title=story_title,
                        step_title=step_title,
                        tone=tone,
                        location=step_location,
                    )
                )
            else:
                recommended = CANONICAL_TONE_ICONS.get(tone, ())
                if recommended and icon not in recommended:
                    findings.append(
                        rule_icon_tone_mismatch(
                            story_title=story_title,
                            step_title=step_title,
                            tone=tone,
                            icon=icon,
                            recommended=recommended,
                            location=step_location,
                        )
                    )

    if step_count >= MIN_STEPS_FOR_TONE_OVERUSE and non_neutral_count == step_count:
        findings.append(
            rule_tone_overuse(
                story_title=story_title,
                location=story_location,
            )
        )
    return findings


def rule_tone_missing_icon(
    *,
    story_title: str,
    step_title: str,
    tone: str,
    location: StoryToneLocation,
) -> StoryToneFinding:
    return StoryToneFinding(
        code="story.tone_missing_icon",
        message=(
            f'Story step "{step_title}" in "{story_title}" uses tone "{tone}" without an icon.'
        ),
        fix="Add a matching icon or remove the tone.",
        location=location,
    )


def rule_icon_tone_mismatch(
    *,
    story_title: str,
    step_title: str,
    tone: str,
    icon: str,
    recommended: tuple[str, ...],
    location: StoryToneLocation,
) -> StoryToneFinding:
    suggestions = ", ".join(recommended) if recommended else "none"
    return StoryToneFinding(
        code="story.icon_tone_mismatch",
        message=(
            f'Story step "{step_title}" in "{story_title}" uses icon "{icon}" '
            f'with tone "{tone}".'
        ),
        fix=f"Use a tone-aligned icon ({suggestions}) or adjust the tone.",
        location=location,
    )


def rule_tone_overuse(*, story_title: str, location: StoryToneLocation) -> StoryToneFinding:
    return StoryToneFinding(
        code="story.tone_overuse",
        message=f'Story "{story_title}" marks every step with a non-neutral tone.',
        fix="Reserve tones for steps that signal status and keep other steps neutral.",
        location=location,
    )


def _normalize_label(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


__all__ = [
    "CANONICAL_TONE_ICONS",
    "MIN_STEPS_FOR_TONE_OVERUSE",
    "NON_NEUTRAL_TONES",
    "StoryToneFinding",
    "StoryToneLocation",
    "collect_story_tone_findings",
    "rule_icon_tone_mismatch",
    "rule_tone_missing_icon",
    "rule_tone_overuse",
]
