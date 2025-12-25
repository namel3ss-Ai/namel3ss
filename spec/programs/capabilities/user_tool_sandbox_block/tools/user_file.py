from __future__ import annotations


def run(payload: dict) -> dict:
    path = payload.get("path", "blocked.txt")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("blocked")
    return {"ok": True, "path": path}
