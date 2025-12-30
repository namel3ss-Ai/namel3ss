def run(payload: dict) -> dict:
    name = payload.get("name") or "there"
    return {"message": f"Hello {name}"}
