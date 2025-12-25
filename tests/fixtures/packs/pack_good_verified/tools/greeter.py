from __future__ import annotations


def run(payload: dict) -> dict:
    name = payload.get("name", "world")
    return {"message": f"Hello {name}", "ok": True}
