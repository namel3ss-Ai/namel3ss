def run(payload):
    name = payload.get("name", "")
    count = payload.get("count", 0)
    active = payload.get("active", False)
    return {"message": f"{name}:{count}:{active}"}
