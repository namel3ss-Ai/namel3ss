from __future__ import annotations

from pathlib import Path
from typing import List, Dict
from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode, validate_media_reference
from namel3ss.runtime.flow.gates import evaluate_requires
from namel3ss.ui.manifest.canonical import _element_id, _slugify
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import add_warning

from .base import _base_element


def _story_step_id(element_id: str, title: str, slug_counts: dict[str, int]) -> str:
    slug = _slugify(title) or "step"
    current = slug_counts.get(slug, 0)
    slug_counts[slug] = current + 1
    suffix = slug if current == 0 else f"{slug}.{current}"
    return f"{element_id}.step.{suffix}"


def _build_story_gate(
    step_id: str,
    requires: str | None,
    state_ctx: StateContext,
    warnings: list | None,
    *,
    line: int | None,
    column: int | None,
) -> dict | None:
    if not requires:
        return None
    gate: dict = {"id": f"{step_id}.gate", "requires": requires}
    evaluation = evaluate_requires(requires, state_ctx.state)
    if evaluation.path is not None:
        if evaluation.path:
            gate["path"] = evaluation.path
        if evaluation.issue == "missing":
            add_warning(
                warnings,
                code="state.missing",
                message=f"Story gate requires '{requires}' but no state value was found.",
                fix="Provide the state value or adjust the requires rule.",
                path=evaluation.path,
                line=line,
                column=column,
            )
        elif evaluation.issue == "invalid":
            add_warning(
                warnings,
                code="state.invalid",
                message="Story gate requires state path is malformed.",
                fix="Use state.<path> or remove the requires rule.",
                line=line,
                column=column,
            )
    gate["ready"] = evaluation.ready
    gate["reason"] = f"requires {requires}"
    return gate


def build_story_item(
    item: ir.StoryItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    state_ctx: StateContext,
    media_registry: dict[str, Path],
    media_mode: MediaValidationMode,
    warnings: list | None,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "story", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    slug_counts: dict[str, int] = {}
    steps: list[dict] = []
    step_lookup: dict[str, dict] = {}
    for idx, step in enumerate(item.steps):
        step_id = _story_step_id(element_id, step.title, slug_counts)
        gate = _build_story_gate(step_id, step.requires, state_ctx, warnings, line=step.line, column=step.column)
        payload: dict = {
            "type": "story_step",
            "title": step.title,
            "id": step_id,
            "index": idx,
        }
        if step.text:
            payload["text"] = step.text
        if step.icon:
            payload["icon"] = step.icon
        if step.image:
            intent = validate_media_reference(
                step.image,
                registry=media_registry,
                role=step.image_role,
                mode=media_mode,
                warnings=warnings,
                line=step.line,
                column=step.column,
            )
            payload["image"] = intent.as_dict()
        if step.tone:
            payload["tone"] = step.tone
        if step.requires:
            payload["requires"] = step.requires
        if gate:
            payload["gate"] = gate
        steps.append(payload)
        step_lookup[step.title] = payload
    for idx, step in enumerate(item.steps):
        target_title = step.next or (item.steps[idx + 1].title if idx + 1 < len(item.steps) else None)
        if target_title:
            target_payload = step_lookup.get(target_title)
            if target_payload:
                steps[idx]["next"] = {"title": target_title, "target": target_payload.get("id")}
    element = {
        "type": "story",
        "title": item.title,
        "id": element_id,
        "slug": _slugify(item.title),
        "steps": steps,
        "children": steps,
        **base,
    }
    return _attach_origin(element, item), {}


__all__ = ["build_story_item"]
