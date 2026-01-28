from __future__ import annotations

from namel3ss.errors.guidance import build_guidance_message

PURE_VALUE = "pure"
EFFECTFUL_VALUE = "effectful"
SUPPORTED_PURITY = {PURE_VALUE, EFFECTFUL_VALUE}


def normalize_purity(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "impure":
        return EFFECTFUL_VALUE
    if normalized in SUPPORTED_PURITY:
        return normalized
    raise ValueError("purity must be 'pure' or 'effectful'")


def is_pure(value: str | None) -> bool:
    return value == PURE_VALUE


def pure_effect_message(effect: str, *, flow_name: str | None = None) -> str:
    if flow_name:
        what = f'Pure flow "{flow_name}" cannot {effect}.'
    else:
        what = f"Pure flow cannot {effect}."
    return build_guidance_message(
        what=what,
        why="Pure flows must not perform effects.",
        fix='Remove the effect or declare the flow as effectful.',
        example='flow "demo": purity is "effectful"',
    )


__all__ = ["EFFECTFUL_VALUE", "PURE_VALUE", "SUPPORTED_PURITY", "is_pure", "normalize_purity", "pure_effect_message"]
