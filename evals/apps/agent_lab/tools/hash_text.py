import hashlib


def run(payload: dict) -> dict:
    value = payload.get("value")
    if not isinstance(value, str):
        raise ValueError("payload.value must be text")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return {"hash": digest}
