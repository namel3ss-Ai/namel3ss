from __future__ import annotations

from dataclasses import dataclass


TEXT_LENGTH_THRESHOLD = 200
ACTION_LABEL_LENGTH_THRESHOLD = 40

ACTION_LABEL_VERBS = {
    "add",
    "apply",
    "approve",
    "assign",
    "cancel",
    "close",
    "copy",
    "create",
    "delete",
    "download",
    "edit",
    "export",
    "filter",
    "import",
    "invite",
    "open",
    "remove",
    "reset",
    "retry",
    "run",
    "save",
    "search",
    "send",
    "share",
    "start",
    "stop",
    "submit",
    "update",
    "upload",
    "view",
}

DATA_HEAVY_TYPES = {"form", "table", "list", "chart", "chat", "view"}
COPY_CONTAINER_TYPES = {"section", "card", "tab", "modal", "drawer"}
ACTION_ELEMENT_TYPES = {"button", "link"}


@dataclass(frozen=True)
class CopyLocation:
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
class CopyFinding:
    code: str
    message: str
    fix: str
    location: CopyLocation

    def sort_key(self) -> tuple[str, str, int, int, str]:
        path = self.location.path or ""
        return (
            self.code,
            path,
            self.location.line or 0,
            self.location.column or 0,
            self.message,
        )


@dataclass(frozen=True)
class LabelOccurrence:
    label: str
    location: CopyLocation


def collect_copy_findings(pages: list[dict]) -> list[CopyFinding]:
    findings: list[CopyFinding] = []
    for page in pages:
        page_name = str(page.get("name") or page.get("slug") or "page")
        page_slug = str(page.get("slug") or page_name)
        elements = page.get("elements") or []
        if not _has_page_title(elements):
            findings.append(
                rule_missing_page_title(
                    page_name=page_name,
                    location=CopyLocation(
                        page=page_name,
                        page_slug=page_slug,
                        path=_page_path(page_slug),
                        line=None,
                        column=None,
                    ),
                )
            )

        label_occurrences: dict[str, list[LabelOccurrence]] = {}
        first_data_location: CopyLocation | None = None
        text_before_data = False

        def walk(children: list[dict]) -> None:
            nonlocal first_data_location, text_before_data
            for element in children:
                if not isinstance(element, dict):
                    continue
                element_type = element.get("type")
                location = _element_location(page_name, page_slug, element)
                if element_type == "text":
                    text_value = element.get("value")
                    text_length = _text_length(text_value)
                    if text_length > TEXT_LENGTH_THRESHOLD:
                        findings.append(
                            rule_text_too_long(
                                page_name=page_name,
                                text_length=text_length,
                                location=location,
                            )
                        )
                    if first_data_location is None:
                        text_before_data = True
                if element_type in DATA_HEAVY_TYPES and first_data_location is None:
                    first_data_location = location
                if element_type in COPY_CONTAINER_TYPES:
                    label = _normalize_label(element.get("label"))
                    if not label:
                        findings.append(
                            rule_unlabeled_container(
                                container_type=str(element_type),
                                location=location,
                            )
                        )
                    else:
                        key = _label_key(label)
                        label_occurrences.setdefault(key, []).append(
                            LabelOccurrence(label=label, location=location)
                        )
                if element_type in ACTION_ELEMENT_TYPES:
                    action_warning = rule_action_label(label=element.get("label"), location=location)
                    if action_warning:
                        findings.append(action_warning)
                nested = element.get("children")
                if isinstance(nested, list):
                    walk(nested)

        walk(elements)

        if first_data_location is not None and not text_before_data:
            findings.append(
                rule_missing_intro_text(
                    page_name=page_name,
                    location=first_data_location,
                )
            )

        findings.extend(_duplicate_label_findings(page_name=page_name, occurrences=label_occurrences))
    return findings


def rule_missing_page_title(*, page_name: str, location: CopyLocation) -> CopyFinding:
    return CopyFinding(
        code="copy.missing_page_title",
        message=f'Page "{page_name}" has no title.',
        fix="Add a title item near the top of the page.",
        location=location,
    )


def rule_unlabeled_container(*, container_type: str, location: CopyLocation) -> CopyFinding:
    return CopyFinding(
        code="copy.unlabeled_container",
        message=f'Container {container_type} on page "{location.page}" has no label.',
        fix="Provide a label for this container.",
        location=location,
    )


def rule_duplicate_container_label(*, label: str, page_name: str, location: CopyLocation) -> CopyFinding:
    return CopyFinding(
        code="copy.duplicate_container_label",
        message=f'Label "{label}" is reused on page "{page_name}".',
        fix="Use unique labels for sections, cards, tabs, modals, and drawers.",
        location=location,
    )


def rule_missing_intro_text(*, page_name: str, location: CopyLocation) -> CopyFinding:
    return CopyFinding(
        code="copy.missing_intro_text",
        message=f'Page "{page_name}" has data-heavy content without intro text.',
        fix="Add a short text block before the first data-heavy element.",
        location=location,
    )


def rule_text_too_long(*, page_name: str, text_length: int, location: CopyLocation) -> CopyFinding:
    return CopyFinding(
        code="copy.text_too_long",
        message=f'Text block on page "{page_name}" exceeds {TEXT_LENGTH_THRESHOLD} characters.',
        fix="Split into shorter text, move into story blocks, or use multiple cards.",
        location=location,
    )


def rule_action_label(*, label: object, location: CopyLocation) -> CopyFinding | None:
    normalized = _normalize_label(label)
    if not normalized:
        message = f'Action label on page "{location.page}" is empty.'
    elif len(normalized) > ACTION_LABEL_LENGTH_THRESHOLD:
        message = (
            f'Action label "{normalized}" on page "{location.page}" exceeds '
            f"{ACTION_LABEL_LENGTH_THRESHOLD} characters."
        )
    elif not _is_verb_led(normalized):
        message = f'Action label "{normalized}" on page "{location.page}" should start with a verb.'
    else:
        return None
    return CopyFinding(
        code="copy.action_label",
        message=message,
        fix="Use a short verb-first label: 'Create ...', 'View ...', 'Reset ...'.",
        location=location,
    )


def _duplicate_label_findings(
    *,
    page_name: str,
    occurrences: dict[str, list[LabelOccurrence]],
) -> list[CopyFinding]:
    findings: list[CopyFinding] = []
    for key in sorted(occurrences):
        entries = occurrences[key]
        if len(entries) <= 1:
            continue
        ordered = sorted(entries, key=lambda entry: entry.location.sort_key())
        label = ordered[0].label
        location = ordered[0].location
        findings.append(
            rule_duplicate_container_label(
                label=label,
                page_name=page_name,
                location=location,
            )
        )
    return findings


def _has_page_title(elements: list[dict]) -> bool:
    for element in elements:
        if not isinstance(element, dict):
            continue
        if element.get("type") != "title":
            continue
        value = _normalize_label(element.get("value"))
        if value:
            return True
    return False


def _element_location(page_name: str, page_slug: str, element: dict) -> CopyLocation:
    return CopyLocation(
        page=page_name,
        page_slug=page_slug,
        path=element.get("element_id"),
        line=element.get("line"),
        column=element.get("column"),
    )


def _normalize_label(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _label_key(value: str) -> str:
    return value.casefold()


def _text_length(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value)
    return len(str(value))


def _is_verb_led(label: str) -> bool:
    word = _first_word(label)
    if not word:
        return False
    return word.lower() in ACTION_LABEL_VERBS


def _first_word(label: str) -> str:
    if not label:
        return ""
    word = label.split()[0]
    return word.strip("\"'.,:;!?()[]{}")


def _page_path(page_slug: str) -> str:
    return f"page.{page_slug}"


__all__ = [
    "ACTION_ELEMENT_TYPES",
    "ACTION_LABEL_LENGTH_THRESHOLD",
    "ACTION_LABEL_VERBS",
    "COPY_CONTAINER_TYPES",
    "CopyFinding",
    "CopyLocation",
    "DATA_HEAVY_TYPES",
    "LabelOccurrence",
    "TEXT_LENGTH_THRESHOLD",
    "collect_copy_findings",
    "rule_action_label",
    "rule_duplicate_container_label",
    "rule_missing_intro_text",
    "rule_missing_page_title",
    "rule_text_too_long",
    "rule_unlabeled_container",
]
