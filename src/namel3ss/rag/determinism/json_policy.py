from __future__ import annotations

import json
from urllib.parse import urlencode

from namel3ss.determinism import canonical_json_dumps


def canonical_contract_json(value: object, *, pretty: bool = False) -> str:
    return canonical_json_dumps(value, pretty=pretty, drop_run_keys=False)


def canonical_contract_copy(value: object) -> object:
    return json.loads(canonical_contract_json(value, pretty=False))


def canonical_contract_hash(value: object) -> str:
    import hashlib

    payload = canonical_contract_json(value, pretty=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stable_preview_query(*, doc_id: str, page_number: int, citation_id: str) -> str:
    params = [
        ("doc", str(doc_id or "").strip()),
        ("page", str(max(1, int(page_number)))),
        ("cit", str(citation_id or "").strip()),
    ]
    return urlencode(params)


__all__ = [
    "canonical_contract_copy",
    "canonical_contract_hash",
    "canonical_contract_json",
    "stable_preview_query",
]
