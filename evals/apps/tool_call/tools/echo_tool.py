def run(payload):
    text = payload.get("text", "")
    return {"message": str(text)}
