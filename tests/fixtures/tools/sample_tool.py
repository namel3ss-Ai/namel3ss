from __future__ import annotations


def greet(payload: dict) -> dict:
    name = payload.get("name", "world")
    return {"message": f"Hello {name}", "ok": True}


def bad_output(payload: dict) -> str:
    return "not-json"
