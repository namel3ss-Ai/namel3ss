from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.tutorials import (
    DEFAULT_PLAYGROUND_TIMEOUT_SECONDS,
    MAX_PLAYGROUND_TIMEOUT_SECONDS,
    check_snippet,
    list_tutorials,
    load_tutorial_progress,
    run_snippet,
    run_tutorial,
)


def get_tutorials_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    _ = source
    action = str(body.get("action") or "list").strip().lower()
    project_root = Path(app_path).resolve().parent

    if action == "list":
        tutorials = list_tutorials()
        progress = load_tutorial_progress(project_root)
        items: list[dict[str, object]] = []
        for item in tutorials:
            slug = str(item.get("slug") or "")
            status = progress.get(slug) or {}
            merged = dict(item)
            merged["completed"] = bool(status.get("completed", False))
            merged["last_passed"] = int(status.get("last_passed", 0))
            items.append(merged)
        return {"ok": True, "items": items, "count": len(items)}

    if action == "run":
        slug = _read_text(body.get("slug"))
        if not slug:
            raise Namel3ssError(_missing_slug_message())
        answers = body.get("answers")
        parsed_answers = [str(item) for item in answers] if isinstance(answers, list) else None
        payload = run_tutorial(
            slug,
            project_root=project_root,
            answers=parsed_answers,
            auto=bool(body.get("auto", True)),
        )
        return payload

    raise Namel3ssError(_unknown_action_message(action))


def get_playground_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    _ = app_path
    action = str(body.get("action") or "check").strip().lower()
    snippet = _read_text(body.get("source")) or source

    if action == "check":
        payload = check_snippet(snippet)
        payload["action"] = "check"
        return payload

    if action == "run":
        flow_name = _read_text(body.get("flow_name"))
        input_payload = body.get("input")
        timeout_value = body.get("timeout_seconds")
        timeout_seconds = (
            float(timeout_value)
            if isinstance(timeout_value, (int, float))
            else float(DEFAULT_PLAYGROUND_TIMEOUT_SECONDS)
        )
        payload = run_snippet(
            snippet,
            flow_name=flow_name,
            input_payload=input_payload if isinstance(input_payload, dict) else None,
            timeout_seconds=max(0.1, min(timeout_seconds, float(MAX_PLAYGROUND_TIMEOUT_SECONDS))),
        )
        payload["action"] = "run"
        return payload

    raise Namel3ssError(_unknown_playground_action(action))


def _read_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def _missing_slug_message() -> str:
    return build_guidance_message(
        what="Tutorial slug is required.",
        why="Running a tutorial needs a lesson identifier.",
        fix="Choose a slug from n3 tutorial list.",
        example="n3 tutorial run basics",
    )


def _unknown_action_message(action: str) -> str:
    return build_guidance_message(
        what=f"Unknown tutorial action '{action}'.",
        why="Supported actions are list and run.",
        fix="Use action=list or action=run.",
        example='{"action":"list"}',
    )


def _unknown_playground_action(action: str) -> str:
    return build_guidance_message(
        what=f"Unknown playground action '{action}'.",
        why="Supported actions are check and run.",
        fix="Use action=check or action=run.",
        example='{"action":"run"}',
    )


__all__ = ["get_playground_payload", "get_tutorials_payload"]
