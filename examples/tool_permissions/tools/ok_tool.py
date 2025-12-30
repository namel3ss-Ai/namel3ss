from __future__ import annotations


def run(payload: dict) -> dict:
    name = payload.get("name") or "there"
    return {"message": f"Hello {name}"}
