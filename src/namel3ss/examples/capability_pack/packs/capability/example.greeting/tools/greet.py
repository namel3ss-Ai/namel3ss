def run(payload):
    name = payload.get("name") if isinstance(payload, dict) else None
    if not name:
        name = "there"
    return {"message": f"Hello {name}"}
