from __future__ import annotations

import base64

from namel3ss.determinism import canonical_json_dumps


def encode_toon(payload: object) -> str:
    raw = canonical_json_dumps(payload, pretty=False, drop_run_keys=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_toon(token: str) -> object:
    padded = token + "=" * ((4 - len(token) % 4) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    try:
        import json

        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


__all__ = ["decode_toon", "encode_toon"]
