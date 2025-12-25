def run(payload):
    name = payload.get("name", "there")
    return {"message": f"Hello {name}", "ok": True}
