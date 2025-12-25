from __future__ import annotations


def run(payload: dict) -> dict:
    """Generated tool: greeter."""
    # Input schema:
    # - age: number (optional)
    # - name: text (required)
    # Output schema:
    # - message: text (required)
    # - ok: boolean (required)
    return {
        "message": "",
        "ok": False,
    }
