from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.marketplace import approve_item, install_item, item_comments, publish_item, rate_item, search_items



def get_marketplace_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    _ = source
    app_file = Path(app_path)
    action = _text(body.get("action")) or "search"
    registry = _text(body.get("registry")) or None

    if action == "search":
        query = _text(body.get("query"))
        include_pending = bool(body.get("include_pending"))
        items = search_items(
            project_root=app_file.parent,
            app_path=app_file,
            query=query,
            include_pending=include_pending,
            registry_override=registry,
        )
        return {"ok": True, "action": "search", "count": len(items), "items": items}

    if action == "install":
        name = _required_text(body.get("name"), "name")
        version = _text(body.get("version")) or None
        include_pending = bool(body.get("include_pending"))
        payload = install_item(
            project_root=app_file.parent,
            app_path=app_file,
            name=name,
            version=version,
            include_pending=include_pending,
            registry_override=registry,
        )
        payload["action"] = "install"
        return payload

    if action == "publish":
        path = _required_text(body.get("path"), "path")
        payload = publish_item(
            project_root=app_file.parent,
            app_path=app_file,
            item_path=path,
            registry_override=registry,
        )
        payload["action"] = "publish"
        return payload

    if action == "approve":
        name = _required_text(body.get("name"), "name")
        version = _required_text(body.get("version"), "version")
        payload = approve_item(
            project_root=app_file.parent,
            app_path=app_file,
            name=name,
            version=version,
            registry_override=registry,
        )
        payload["action"] = "approve"
        return payload

    if action == "rate":
        name = _required_text(body.get("name"), "name")
        version = _required_text(body.get("version"), "version")
        rating = body.get("rating")
        if isinstance(rating, bool):
            rating = None
        try:
            parsed_rating = int(rating)
        except Exception:
            raise Namel3ssError(_invalid_rating_message())
        comment = _text(body.get("comment"))
        payload = rate_item(
            project_root=app_file.parent,
            app_path=app_file,
            name=name,
            version=version,
            rating=parsed_rating,
            comment=comment,
            registry_override=registry,
        )
        payload["action"] = "rate"
        return payload

    if action == "comments":
        name = _required_text(body.get("name"), "name")
        version = _required_text(body.get("version"), "version")
        comments = item_comments(
            project_root=app_file.parent,
            app_path=app_file,
            name=name,
            version=version,
            registry_override=registry,
        )
        return {"ok": True, "action": "comments", "count": len(comments), "comments": comments}

    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown marketplace action '{action}'.",
            why="Supported actions are search, install, publish, approve, rate, and comments.",
            fix="Use one of the supported actions.",
            example='{"action":"search","query":"prompt"}',
        )
    )



def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()



def _required_text(value: object, field: str) -> str:
    text = _text(value)
    if text:
        return text
    raise Namel3ssError(
        build_guidance_message(
            what=f"Marketplace {field} is missing.",
            why=f"Action requires {field}.",
            fix=f"Provide {field} and retry.",
            example=f'{{"action":"install","{field}":"demo.item"}}',
        )
    )



def _invalid_rating_message() -> str:
    return build_guidance_message(
        what="Marketplace rating is invalid.",
        why="Rating must be an integer from 1 to 5.",
        fix="Provide a rating in range.",
        example='{"action":"rate","name":"demo.item","version":"0.1.0","rating":5}',
    )


__all__ = ["get_marketplace_payload"]
