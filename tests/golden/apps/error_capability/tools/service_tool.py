def run(payload):
    value = payload.get("value", "")
    return {"message": f"pong:{value}"}
