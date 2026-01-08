from __future__ import annotations


def _attach_origin(element: dict, item) -> dict:
    origin = getattr(item, "origin", None)
    if origin:
        ordered: dict = {}
        for key in ("pack", "version", "fragment"):
            if key in origin and origin[key] is not None:
                ordered[key] = origin[key]
        element["origin"] = ordered or dict(origin)
    return element


__all__ = ["_attach_origin"]
