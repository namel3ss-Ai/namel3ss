from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_persistence_root


FEEDBACK_FILENAME = "feedback.jsonl"
ALLOWED_RATINGS = ("excellent", "good", "bad")


@dataclass(frozen=True)
class FeedbackEntry:
    flow_name: str
    input_id: str
    rating: str
    comment: str
    step_count: int

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "flow_name": self.flow_name,
            "input_id": self.input_id,
            "rating": self.rating,
            "step_count": int(self.step_count),
        }
        if self.comment:
            payload["comment"] = self.comment
        return payload



def feedback_path(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    allow_create: bool = True,
) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / FEEDBACK_FILENAME



def load_feedback_entries(project_root: str | Path | None, app_path: str | Path | None) -> list[FeedbackEntry]:
    path = feedback_path(project_root, app_path, allow_create=False)
    if path is None or not path.exists():
        return []
    entries: list[FeedbackEntry] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as err:
            raise Namel3ssError(_invalid_feedback_file_message(path, err.msg)) from err
        entry = _entry_from_payload(payload, path=path)
        if entry is not None:
            entries.append(entry)
    return sorted(entries, key=lambda item: (item.step_count, item.flow_name, item.input_id, item.rating, item.comment))



def append_feedback_entry(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    flow_name: str,
    input_id: str,
    rating: str,
    comment: str | None = None,
    step_count: int | None = None,
) -> FeedbackEntry:
    path = feedback_path(project_root, app_path)
    if path is None:
        raise Namel3ssError(
            build_guidance_message(
                what="Feedback path could not be resolved.",
                why="The project root is missing.",
                fix="Run the command from a project with app.ai.",
                example="n3 feedback list",
            )
        )
    existing = load_feedback_entries(project_root, app_path)
    resolved_step = _resolve_step_count(existing, step_count)
    entry = FeedbackEntry(
        flow_name=_require_text(flow_name, "flow_name"),
        input_id=_require_text(input_id, "input_id"),
        rating=_require_rating(rating),
        comment=(comment or "").strip(),
        step_count=resolved_step,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json_dumps(entry.to_dict(), pretty=False, drop_run_keys=False) + "\n")
    return entry



def summarize_feedback(entries: list[FeedbackEntry]) -> dict[str, object]:
    total = len(entries)
    excellent = len([item for item in entries if item.rating == "excellent"])
    good = len([item for item in entries if item.rating == "good"])
    bad = len([item for item in entries if item.rating == "bad"])
    positive = excellent + good
    positive_ratio = float(positive / total) if total else 1.0
    completion_quality = float(((1.0 * excellent) + (0.8 * good) + (0.0 * bad)) / total) if total else 1.0
    return {
        "total": total,
        "excellent": excellent,
        "good": good,
        "bad": bad,
        "positive_ratio": positive_ratio,
        "completion_quality": completion_quality,
    }



def _entry_from_payload(payload: object, *, path: Path) -> FeedbackEntry | None:
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_feedback_file_message(path, "entry is not an object"))
    flow_name = payload.get("flow_name")
    input_id = payload.get("input_id")
    rating = payload.get("rating")
    step_count = payload.get("step_count")
    comment = payload.get("comment")
    if not isinstance(flow_name, str) or not flow_name.strip():
        raise Namel3ssError(_invalid_feedback_file_message(path, "flow_name is missing"))
    if not isinstance(input_id, str) or not input_id.strip():
        raise Namel3ssError(_invalid_feedback_file_message(path, "input_id is missing"))
    if not isinstance(rating, str) or rating.strip() not in ALLOWED_RATINGS:
        raise Namel3ssError(_invalid_feedback_file_message(path, "rating is invalid"))
    parsed_step = _parse_step_count(step_count)
    if parsed_step is None:
        raise Namel3ssError(_invalid_feedback_file_message(path, "step_count is invalid"))
    parsed_comment = comment.strip() if isinstance(comment, str) else ""
    return FeedbackEntry(
        flow_name=flow_name.strip(),
        input_id=input_id.strip(),
        rating=rating.strip(),
        comment=parsed_comment,
        step_count=parsed_step,
    )



def _resolve_step_count(existing: list[FeedbackEntry], value: int | None) -> int:
    if value is not None:
        parsed = _parse_step_count(value)
        if parsed is None:
            raise Namel3ssError(_invalid_feedback_input_message("step_count must be a non-negative integer."))
        return parsed
    if not existing:
        return 1
    return max(item.step_count for item in existing) + 1



def _parse_step_count(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except Exception:
        return None
    if parsed < 0:
        return None
    return parsed



def _require_text(value: str, field: str) -> str:
    text = str(value or "").strip()
    if text:
        return text
    raise Namel3ssError(_invalid_feedback_input_message(f"{field} is required."))



def _require_rating(value: str) -> str:
    rating = str(value or "").strip()
    if rating in ALLOWED_RATINGS:
        return rating
    allowed = ", ".join(ALLOWED_RATINGS)
    raise Namel3ssError(_invalid_feedback_input_message(f"rating must be one of: {allowed}."))



def _invalid_feedback_file_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="Feedback file is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Delete invalid rows or recreate the file.",
        example='{"flow_name":"ask_ai","input_id":"abc123","rating":"good","step_count":1}',
    )



def _invalid_feedback_input_message(details: str) -> str:
    return build_guidance_message(
        what="Feedback entry is invalid.",
        why=details,
        fix="Provide required fields with valid values.",
        example='{"flow_name":"ask_ai","input_id":"abc123","rating":"good"}',
    )


__all__ = [
    "ALLOWED_RATINGS",
    "FEEDBACK_FILENAME",
    "FeedbackEntry",
    "append_feedback_entry",
    "feedback_path",
    "load_feedback_entries",
    "summarize_feedback",
]
