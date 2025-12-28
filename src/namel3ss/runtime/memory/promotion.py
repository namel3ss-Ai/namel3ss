from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.memory.spaces import MEMORY_SPACES, SPACE_PROJECT, SPACE_SYSTEM, SPACE_USER


@dataclass(frozen=True)
class PromotionRequest:
    target_space: str
    reason: str


_PROMOTION_HINTS = {
    SPACE_USER: [
        ("remember this for me", "hint:remember_for_me"),
        ("remember this about me", "hint:remember_about_me"),
        ("save this for me", "hint:save_for_me"),
    ],
    SPACE_PROJECT: [
        ("remember this for the project", "hint:remember_for_project"),
        ("remember this for my project", "hint:remember_for_project"),
        ("remember this for our project", "hint:remember_for_project"),
        ("project memory", "hint:project_memory"),
    ],
    SPACE_SYSTEM: [
        ("remember this for everyone", "hint:remember_for_everyone"),
        ("remember this for the system", "hint:remember_for_system"),
        ("system memory", "hint:system_memory"),
    ],
}


def infer_promotion_request(text: str) -> PromotionRequest | None:
    lowered = text.lower()
    for space, patterns in _PROMOTION_HINTS.items():
        for snippet, reason in patterns:
            if snippet in lowered:
                return PromotionRequest(target_space=space, reason=reason)
    return None


def promotion_request_for_item(item) -> PromotionRequest | None:
    meta = getattr(item, "meta", None) or {}
    target = meta.get("promotion_target")
    if isinstance(target, str) and target in MEMORY_SPACES:
        reason = meta.get("promotion_reason") or "meta:promotion_target"
        return PromotionRequest(target_space=target, reason=str(reason))
    text = getattr(item, "text", "") or ""
    return infer_promotion_request(text)


__all__ = ["PromotionRequest", "infer_promotion_request", "promotion_request_for_item"]
