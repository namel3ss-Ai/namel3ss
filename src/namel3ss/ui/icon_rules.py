from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ui.manifest.page_structure import page_root_elements

NEUTRAL_TONE = "neutral"


@dataclass(frozen=True)
class IconLocation:
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
class IconFinding:
    code: str
    message: str
    fix: str
    location: IconLocation

    def sort_key(self) -> tuple[str, str, int, int, str]:
        path = self.location.path or ""
        return (
            self.code,
            path,
            self.location.line or 0,
            self.location.column or 0,
            self.message,
        )


def collect_icon_findings(pages: list[dict]) -> list[IconFinding]:
    findings: list[IconFinding] = []
    tone_icons: dict[str, dict[str, list[IconLocation]]] = {}
    for page in pages:
        page_name = str(page.get("name") or page.get("slug") or "page")
        page_slug = str(page.get("slug") or page_name)
        elements = page_root_elements(page)
        _walk_story_elements(page_name, page_slug, elements, findings, tone_icons)
    findings.extend(_icon_inconsistency_findings(tone_icons))
    return findings


def _walk_story_elements(
    page_name: str,
    page_slug: str,
    elements: list[dict],
    findings: list[IconFinding],
    tone_icons: dict[str, dict[str, list[IconLocation]]],
) -> None:
    for element in elements:
        if not isinstance(element, dict):
            continue
        if element.get("type") == "story":
            findings.extend(_icon_findings_for_story(page_name, page_slug, element, tone_icons))
        nested = element.get("children")
        if isinstance(nested, list):
            _walk_story_elements(page_name, page_slug, nested, findings, tone_icons)


def _icon_findings_for_story(
    page_name: str,
    page_slug: str,
    element: dict,
    tone_icons: dict[str, dict[str, list[IconLocation]]],
) -> list[IconFinding]:
    steps = element.get("steps")
    if not isinstance(steps, list):
        return []
    story_title = _normalize_label(element.get("title")) or "Story"
    story_path = element.get("element_id") or element.get("id")
    line = element.get("line")
    column = element.get("column")
    story_location = IconLocation(
        page=page_name,
        page_slug=page_slug,
        path=story_path,
        line=line,
        column=column,
    )
    findings: list[IconFinding] = []
    icon_count = 0
    step_count = 0

    for step in steps:
        if not isinstance(step, dict):
            continue
        step_count += 1
        tone = _normalize_label(step.get("tone"))
        icon = _normalize_label(step.get("icon"))
        step_title = _normalize_label(step.get("title")) or "step"
        step_path = step.get("id") or story_path
        step_location = IconLocation(
            page=page_name,
            page_slug=page_slug,
            path=step_path,
            line=line,
            column=column,
        )
        if icon:
            icon_count += 1
            if not tone or tone == NEUTRAL_TONE:
                findings.append(
                    rule_icon_misuse(
                        story_title=story_title,
                        step_title=step_title,
                        icon=icon,
                        location=step_location,
                    )
                )
            else:
                tone_icons.setdefault(tone, {}).setdefault(icon, []).append(step_location)

    if icon_count > 1:
        findings.append(
            rule_icon_overuse(
                story_title=story_title,
                icon_count=icon_count,
                step_count=step_count,
                location=story_location,
            )
        )
    return findings


def _icon_inconsistency_findings(
    tone_icons: dict[str, dict[str, list[IconLocation]]],
) -> list[IconFinding]:
    findings: list[IconFinding] = []
    for tone in sorted(tone_icons):
        icons = tone_icons[tone]
        if len(icons) <= 1:
            continue
        icon_names = sorted(icons)
        location = _pick_location([loc for locations in icons.values() for loc in locations])
        findings.append(
            rule_icon_inconsistent_semantics(
                tone=tone,
                icons=icon_names,
                location=location,
            )
        )
    return findings


def _pick_location(locations: list[IconLocation]) -> IconLocation:
    if not locations:
        return IconLocation(page="page", page_slug="page", path=None, line=None, column=None)
    return sorted(locations, key=lambda entry: entry.sort_key())[0]


def rule_icon_misuse(
    *,
    story_title: str,
    step_title: str,
    icon: str,
    location: IconLocation,
) -> IconFinding:
    return IconFinding(
        code="icon.misuse",
        message=(
            f'Icon "{icon}" is used on a neutral step "{step_title}" in story "{story_title}".'
        ),
        fix="Remove the icon or add a non-neutral tone that matches its meaning.",
        location=location,
    )


def rule_icon_inconsistent_semantics(
    *,
    tone: str,
    icons: list[str],
    location: IconLocation,
) -> IconFinding:
    joined = ", ".join(icons)
    return IconFinding(
        code="icon.inconsistent_semantics",
        message=f'Tone "{tone}" uses multiple icons across the app: {joined}.',
        fix="Use one icon per semantic tone across the app.",
        location=location,
    )


def rule_icon_overuse(
    *,
    story_title: str,
    icon_count: int,
    step_count: int,
    location: IconLocation,
) -> IconFinding:
    if step_count > 1 and icon_count == step_count:
        message = f'Story "{story_title}" uses icons on every step.'
    else:
        message = f'Story "{story_title}" uses {icon_count} icons across steps.'
    return IconFinding(
        code="icon.overuse",
        message=message,
        fix="Reserve icons for the most important steps or containers.",
        location=location,
    )


def _normalize_label(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


__all__ = [
    "IconFinding",
    "IconLocation",
    "NEUTRAL_TONE",
    "collect_icon_findings",
    "rule_icon_inconsistent_semantics",
    "rule_icon_misuse",
    "rule_icon_overuse",
]
