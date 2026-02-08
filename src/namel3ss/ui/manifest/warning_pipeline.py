from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from namel3ss.ui.manifest.diagnostics_warnings import append_diagnostics_warnings
from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest.upload_warnings import append_upload_warnings
from namel3ss.ui.manifest.validation import (
    append_consistency_warnings,
    append_copy_warnings,
    append_layout_warnings,
    append_story_icon_warnings,
    append_visibility_warnings,
)


AppendWarningsFn = Callable[[list[dict], list | None, dict | None], None]


@dataclass(frozen=True)
class WarningPipelineStep:
    name: str
    category: str
    append_fn: AppendWarningsFn


UI_WARNING_PIPELINE: tuple[WarningPipelineStep, ...] = (
    WarningPipelineStep(name="layout", category="layout", append_fn=append_layout_warnings),
    WarningPipelineStep(name="upload", category="upload", append_fn=append_upload_warnings),
    WarningPipelineStep(name="visibility", category="visibility", append_fn=append_visibility_warnings),
    WarningPipelineStep(name="diagnostics", category="diagnostics", append_fn=append_diagnostics_warnings),
    WarningPipelineStep(name="copy", category="copy", append_fn=append_copy_warnings),
    WarningPipelineStep(name="story_icon", category="story/icon", append_fn=append_story_icon_warnings),
    WarningPipelineStep(name="consistency", category="consistency", append_fn=append_consistency_warnings),
)


def append_manifest_warnings(pages: list[dict], warnings: list | None, *, context: dict | None = None) -> None:
    for step in UI_WARNING_PIPELINE:
        try:
            step.append_fn(pages, warnings, context)
        except Exception as err:  # pragma: no cover - defensive guard rail
            raise Namel3ssError(
                f"UI warning pipeline failed during '{step.name}'.",
                details={
                    "pipeline_step": step.name,
                    "pipeline_category": step.category,
                },
            ) from err


def warning_pipeline_names() -> tuple[str, ...]:
    return tuple(step.name for step in UI_WARNING_PIPELINE)


__all__ = ["UI_WARNING_PIPELINE", "WarningPipelineStep", "append_manifest_warnings", "warning_pipeline_names"]
