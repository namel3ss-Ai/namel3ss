
def run(payload: dict) -> dict:
    url = payload.get("url")
    if not isinstance(url, str):
        raise ValueError("payload.url must be text")
    return {"status": "blocked"}
